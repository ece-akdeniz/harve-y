"""Owned serial arena operations with durable logical POST provenance."""

import json

from arena_kit.client import ArenaClient, ArenaError

from negotiator.state import Journal


class JournaledArena(ArenaClient):
    def __init__(self, journal_path, **kwargs):
        kwargs["retries"] = 0
        super().__init__(**kwargs)
        self.journal = Journal(journal_path)

    def _call(self, method, path, body=None, params=None, raw=False):
        if method != "POST":
            return super()._call(method, path, body, params, raw)
        # Persist exact public payload before any network operation. Uncertain outcomes never retry.
        case = body.get("case_id", "") if isinstance(body, dict) else ""
        intent = self.journal.intent(case, None, None, "serial-post", body, path=path)
        self._pace()
        response = self.http.request(method, path, json=body, params=params, headers={"X-Move-Id": intent["move_id"]})
        remaining = response.headers.get("X-Practice-Remaining", "")
        if remaining.isdigit():
            self.practice_remaining = int(remaining)
        if response.status_code >= 400:
            self.journal.outcome(intent["move_id"], "failed", http=response.status_code)
            raise ArenaError(response.status_code, "serial request rejected")
        self.journal.outcome(intent["move_id"], "done", http=response.status_code)
        return response.content if raw else json.loads(response.content)
