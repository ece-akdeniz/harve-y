"""Authenticated loop transport with bounded, credential-free errors."""

from urllib.parse import quote

import httpx

from .models import safe_url


class LoopError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class LoopClient:
    def __init__(self, url, token, *, transport=None):
        if not url or not token:
            raise ValueError("LAB_URL and LAB_UPLOAD_TOKEN are required")
        self.http = httpx.Client(
            base_url=safe_url(url).rstrip("/") + "/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
            transport=transport,
            follow_redirects=False,
        )

    def close(self):
        self.http.close()

    def _request(self, method, name, key=None, body=None):
        path = "api/loop/" + quote(name, safe="")
        if key is not None:
            path += "/" + quote(key, safe="")
        try:
            response = self.http.request(method, path, json=body)
        except httpx.HTTPError:
            raise LoopError("transport_unavailable", "Lab unavailable; saved state may be synced safely") from None
        if response.status_code != 200:
            code = {401: "authentication_required", 404: "not_found", 409: "state_conflict"}.get(
                response.status_code, "invalid_input"
            )
            raise LoopError(code, "Lab request rejected; inspect campaign status and local state")
        try:
            value = response.json()
            if not isinstance(value, dict):
                raise ValueError
            return value
        except ValueError:
            raise LoopError("invalid_response", "Lab returned an invalid response") from None

    def read(self, resource, key=None):
        return self._request("GET", resource, key)

    def write(self, operation, body):
        return self._request("POST", operation, body=body)
