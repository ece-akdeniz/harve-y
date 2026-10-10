"""One-port dashboard service. Cookies grant reads; bearer tokens grant uploads."""

import hashlib
import hmac
import json
import secrets
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from pydantic import ValidationError

from .loop_store import LoopStore
from .models import MAX_PAYLOAD, Run
from .store import Conflict, Store

COOKIE = "lab_session"
SESSION_LIFETIME = 12 * 3600


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store: Store, *, password: str, upload_token: str, secure_cookie=False):
        if not password or not upload_token:
            raise ValueError("dashboard password and upload token are required")
        self.store = store
        self.loop_store = LoopStore(store.path)
        self.password_hash = hashlib.sha256(password.encode()).digest()
        self.token_hash = hashlib.sha256(upload_token.encode()).digest()
        self.secure_cookie = secure_cookie
        self.sessions = {}
        self.login_failures = {}
        self.auth_lock = threading.Lock()
        self.request_slots = threading.BoundedSemaphore(64)
        super().__init__(address, Handler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(10)
        return connection, address

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.request_slots.release()

    def handle_error(self, request, client_address):
        # Standard socketserver tracebacks may include arbitrary upstream payloads.
        pass


class Handler(BaseHTTPRequestHandler):
    server: DashboardServer

    def log_message(self, format, *args):
        # Request URLs, bodies, auth headers and remote exception text are never logged.
        pass

    def _json(self, status, value, *, cookie=None):
        data = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(data)

    def _error(self, status, message):
        self._json(status, {"error": message})

    def _body(self):
        try:
            size = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            self._error(400, "invalid JSON body")
            return None
        if size > MAX_PAYLOAD:
            self._error(413, "payload too large")
            return None
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self._error(400, "JSON content type required")
            return None
        if size < 0 or self.headers.get("Transfer-Encoding"):
            self._error(400, "invalid JSON body")
            return None
        try:
            value = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeDecodeError, RecursionError):
            self._error(400, "invalid JSON body")
            return None
        if not isinstance(value, dict):
            self._error(400, "invalid JSON body")
            return None
        return value

    def _bearer(self):
        raw = self.headers.get("Authorization", "")
        return raw.startswith("Bearer ") and hmac.compare_digest(
            hashlib.sha256(raw[7:].encode()).digest(), self.server.token_hash
        )

    def _cookie_value(self):
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            return cookie[COOKIE].value if COOKIE in cookie else None
        except Exception:
            return None

    def _authenticated(self, write=False):
        if self._bearer():
            return True
        if not write:
            session = self._cookie_value()
            with self.server.auth_lock:
                expiry = self.server.sessions.get(session, 0)
                if expiry > time.monotonic():
                    return True
                self.server.sessions.pop(session, None)
        self._error(401, "authentication required")
        return False

    def _cookie(self, value, max_age=SESSION_LIFETIME):
        secure = "; Secure" if self.server.secure_cookie else ""
        return f"{COOKIE}={value}; Path=/; Max-Age={max_age}; HttpOnly; SameSite=Strict{secure}"

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/api/login":
            peer, now = self.client_address[0], time.monotonic()
            with self.server.auth_lock:
                failures = [t for t in self.server.login_failures.get(peer, []) if t > now - 60]
                self.server.login_failures[peer] = failures
                blocked = len(failures) >= 5
            if blocked:
                self._error(429, "too many login attempts; try again later")
                return
            body = self._body()
            if body is None:
                return
            password = body.get("password")
            valid = (
                set(body) == {"password"}
                and isinstance(password, str)
                and len(password) <= 4096
                and hmac.compare_digest(hashlib.sha256(password.encode()).digest(), self.server.password_hash)
            )
            if not valid:
                with self.server.auth_lock:
                    self.server.login_failures[peer].append(now)
                self._error(401, "invalid password")
                return
            session = secrets.token_urlsafe(32)
            with self.server.auth_lock:
                self.server.sessions = {k: v for k, v in self.server.sessions.items() if v > now}
                if len(self.server.sessions) >= 1000:
                    self._error(429, "too many login sessions")
                    return
                self.server.sessions[session] = now + SESSION_LIFETIME
                self.server.login_failures.pop(peer, None)
            self._json(200, {"ok": True}, cookie=self._cookie(session))
        elif path == "/api/logout":
            if not self._authenticated():
                return
            with self.server.auth_lock:
                self.server.sessions.pop(self._cookie_value(), None)
            self._json(200, {"ok": True}, cookie=self._cookie("", 0))
        elif path.startswith("/api/loop/"):
            if not self._authenticated(write=True):
                return
            body = self._body()
            if body is None:
                return
            operation = unquote(path[len("/api/loop/"):])
            try:
                result = self.server.loop_store.write(operation, body)
            except Conflict:
                self._error(409, "loop state conflict")
            except (ValidationError, ValueError, TypeError, RecursionError):
                self._error(400, "invalid loop request")
            else:
                self._json(200, result)
        else:
            self._error(404, "route not found")

    def do_PUT(self):
        if not self._authenticated(write=True):
            return
        path = urlsplit(self.path).path
        if not path.startswith("/api/runs/"):
            self._error(404, "route not found")
            return
        body = self._body()
        if body is None:
            return
        try:
            run = Run.model_validate(body)
            if run.run_id != unquote(path[len("/api/runs/") :]):
                raise ValueError("ID mismatch")
            accepted = self.server.store.upsert(run)
        except Conflict as error:
            self._error(409, str(error))
        except (ValidationError, ValueError, TypeError, RecursionError):
            self._error(400, "invalid run snapshot")
        else:
            self._json(200, {"ok": True, "accepted": accepted})

    def do_GET(self):
        parts = urlsplit(self.path)
        path = parts.path
        if path.startswith("/api/"):
            if not self._authenticated():
                return
            if path.startswith("/api/loop/"):
                route = unquote(path[len("/api/loop/"):]).split("/")
                try:
                    if len(route) > 2:
                        raise ValueError("invalid route")
                    body = self.server.loop_store.read(route[0], route[1] if len(route) == 2 else None)
                except (ValueError, TypeError):
                    self._error(404, "loop resource not found")
                else:
                    self._json(200, body)
            elif path == "/api/runs":
                self._json(200, self.server.store.listing())
            elif path.startswith("/api/runs/"):
                body = self.server.store.get(unquote(path[len("/api/runs/") :]))
                self._json(200, body) if body else self._error(404, "run not found")
            elif path == "/api/compare":
                params = parse_qs(parts.query)
                body = self.server.store.comparison(params.get("baseline", [""])[0], params.get("candidate", [""])[0])
                self._json(200, body) if body else self._error(404, "run not found")
            else:
                self._error(404, "route not found")
            return
        assets = {
            "/": ("index.html", "text/html"),
            "/index.html": ("index.html", "text/html"),
            "/app.js": ("app.js", "application/javascript"),
            "/loop.js": ("loop.js", "application/javascript"),
            "/app.css": ("app.css", "text/css"),
            "/static/app.js": ("app.js", "application/javascript"),
            "/static/app.css": ("app.css", "text/css"),
        }
        if path not in assets:
            self._error(404, "route not found")
            return
        name, content_type = assets[path]
        asset = Path(__file__).parent / "static" / name
        if not asset.is_file():
            self._error(404, "asset not found")
            return
        data = asset.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        self.end_headers()
        self.wfile.write(data)
