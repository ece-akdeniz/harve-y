"""Owned serial arena operations with durable logical POST provenance."""

import hashlib
import json

import httpx
from arena_kit.client import ArenaClient, ArenaError

from negotiator.client import assert_allowed
from negotiator.state import Journal


class RecoveryRequired(RuntimeError):
    """An owned logical POST must be reconciled before any further mutation."""


class JournaledArena(ArenaClient):
    def __init__(self, journal_path, **kwargs):
        kwargs["retries"] = 0
        super().__init__(**kwargs)
        self.journal = Journal(journal_path)

    def _call(self, method, path, body=None, params=None, raw=False):
        assert_allowed(path)
        if method != "POST":
            return super()._call(method, path, body, params, raw)
        if self.journal.pending():
            raise RecoveryRequired("pending Arena submission; reconcile the existing operation first")
        # Persist exact public payload before any network operation. Uncertain outcomes never retry.
        case = body.get("case_id", "") if isinstance(body, dict) else ""
        segments = path.strip("/").split("/")
        session = segments[1] if len(segments) > 1 and segments[0] == "sessions" else None
        supplier = segments[3] if len(segments) > 3 and segments[2] == "threads" else None
        # Spend limiter wait before the final owned-state read. The exact operation is
        # then journaled immediately before its one HTTP attempt.
        self._pace()
        current = self.thread(session, supplier) if session and supplier else None
        before = current["messages"] if current is not None else None
        final_check = getattr(self, "pre_post_check", None)
        if callable(final_check) and supplier and current is not None:
            final_check(supplier, body.get("message", body), current)
        encoded = json.dumps(body, ensure_ascii=False, allow_nan=False, sort_keys=True,
                             separators=(",", ":")).encode()
        intent = self.journal.intent(case, session, supplier, "serial-post", body, path=path,
            payload_utf8=encoded.decode(), payload_hash=hashlib.sha256(encoded).hexdigest(),
            before_messages=before)
        # Journal fsync can be slow enough to consume the remaining permit. This final
        # local check must not perform network I/O: if it fails, close the intent as
        # proven-not-dispatched and do not hand bytes to the HTTP client.
        pre_http_check = getattr(self, "pre_http_check", None)
        if callable(pre_http_check) and session and supplier:
            try:
                pre_http_check(supplier, body.get("message", body), intent)
            except Exception as error:
                self.journal.outcome(intent["move_id"], "failed", reason="proven_not_dispatched",
                                     dispatched=False, detail=type(error).__name__)
                raise
        try:
            response = self.http.request(method, path, content=encoded, params=params,
                headers={"X-Move-Id": intent["move_id"], "Content-Type": "application/json"})
        except httpx.TransportError:
            self.journal.outcome(intent["move_id"], "unresolved", reason="transport_uncertain")
            raise RecoveryRequired("Arena submission outcome uncertain; no retry was made") from None
        remaining = response.headers.get("X-Practice-Remaining", "")
        if remaining.isdigit():
            self.practice_remaining = int(remaining)
        if response.status_code >= 400:
            # A server error may occur after mutation. Never treat it as proven rejection.
            uncertain = response.status_code >= 500 or response.status_code in {408, 429}
            self.journal.outcome(intent["move_id"], "unresolved" if uncertain else "failed",
                                 http=response.status_code)
            if uncertain:
                raise RecoveryRequired("Arena HTTP outcome uncertain; reconcile before another move")
            raise ArenaError(response.status_code, "serial request rejected")
        try:
            result = response.content if raw else json.loads(response.content)
        except ValueError:
            self.journal.outcome(intent["move_id"], "unresolved", reason="invalid_acknowledgement")
            raise RecoveryRequired("Arena acknowledgement malformed; reconcile the existing operation") from None
        self.journal.outcome(intent["move_id"], "done", http=response.status_code, response=result if not raw else None)
        if path == "/sessions" and isinstance(result, dict) and result.get("session_id"):
            self.journal.session(case, result["session_id"], result.get("case"))
        return result

    def reconcile_pending(self):
        """Read-only proof of acknowledged owned messages; never retries or opens sessions."""
        results = []
        for intent in self.journal.pending():
            session, supplier = intent.get("session"), intent.get("supplier")
            if not session or not supplier or intent.get("before_messages") is None:
                results.append({"move_id": intent["move_id"], "status": "recovery_required"})
                continue  # Uncertain opens cannot be assigned by guessing from session listings.
            state = self.session(session)
            current = self.thread(session, supplier)["messages"]
            before = intent["before_messages"]
            expected = {**intent["payload"]["message"], "from": "buyer"}
            # Exact preserved prefix and the first next buyer message prove this serial operation.
            following = current[len(before):] if current[:len(before)] == before else []
            buyer = next((message for message in following if message.get("from") == "buyer"), None)
            acknowledged = buyer == expected
            if acknowledged:
                self.journal.outcome(intent["move_id"], "done", reconciled=True,
                                     response={"state": state, "thread_messages": current})
            results.append({"move_id": intent["move_id"],
                            "status": "acknowledged" if acknowledged else "recovery_required",
                            "terminal": state.get("status") == "ended"})
        return results
