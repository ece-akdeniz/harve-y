"""Opt-in connection probe via an OpenAI-compatible endpoint; no calls at import/init."""

import json
import math
import os
import time
from urllib.parse import urlsplit

import httpx

from .agent import PackageAgent
from .budget import HARD_TIMEOUT_S, bounded

STYLES = {
    "concise": "Please let us know whether you can confirm this package.",
    "collaborative": "We welcome your feedback on the proposed package.",
}
PROMPT = (
    'Choose a business-email closing style. Return only a JSON object '
    'with one field, "style", whose value is "concise" or "collaborative".'
)


class InferenceConnection:
    """Requires organizer-confirmed chat/completions compatibility, URL and model ID."""

    def __init__(self):
        if os.environ.get("LLM_PROVIDER") != "openai":
            raise ValueError("configure LLM_PROVIDER=openai only for a confirmed OpenAI-compatible endpoint")
        self.base = os.environ.get("LLM_BASE_URL", "").rstrip("/")
        self.model = os.environ.get("LLM_MODEL", "")
        self._key = os.environ.get("LLM_API_KEY", "")
        if not self.base or not self.model or not self._key:
            raise ValueError("configure LLM_BASE_URL, LLM_MODEL and LLM_API_KEY before inference experiments")
        url = urlsplit(self.base)
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if (not url.hostname or url.username or url.password or url.query or url.fragment
                or (url.scheme != "https" and not (url.scheme == "http" and local))):
            raise ValueError("inference URL must use HTTPS or loopback HTTP without embedded credentials")
        self.timeout = float(os.environ.get("LLM_TIMEOUT_S", "2"))
        if not math.isfinite(self.timeout) or not 0.1 <= self.timeout <= 5:
            raise ValueError("LLM_TIMEOUT_S must be between 0.1 and 5 seconds per HTTP phase")

    def choose_style(self):
        # A fixed prompt sends no supplier text, prices, private analysis or credentials as content.
        with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
            response = client.post(
                self.base + "/chat/completions",
                headers={"Authorization": "Bearer " + self._key},
                json={"model": self.model, "messages": [{"role": "user", "content": PROMPT}],
                      "max_tokens": 64},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str) or len(content) > 1024:
            raise ValueError("invalid inference response")
        choice = json.loads(content)
        if not isinstance(choice, dict) or set(choice) != {"style"} or choice["style"] not in STYLES:
            raise ValueError("invalid inference style")
        return choice["style"]


class InferenceProbeAgent(PackageAgent):
    """Serial Lab exploratory agent: one real inference call per case, fixed closing choices.

    A connection experiment, not a new economic policy or general LLM writer. Construction
    validates configuration only. Model failures preserve the original deterministic move.
    """

    version = "PackageAgent-inference-probe-v1"

    def __init__(self, *, complete=None, **kwargs):
        super().__init__(**kwargs)
        self._complete = complete or InferenceConnection().choose_style
        self._styles = {}
        self._inference_events = []

    def propose(self, case, threads, supplier_id):
        move = super().propose(case, threads, supplier_id)
        message = move.get("message") or {}
        if message.get("action") or not message.get("term_sheets"):
            return move
        cid = case["case_id"]
        if cid not in self._styles:
            started = time.monotonic()
            status, style = "ok", None
            try:
                style = bounded(self._complete, HARD_TIMEOUT_S)  # per-phase timeout <= 5 s; 8 s wall clock
                if not isinstance(style, str) or style not in STYLES:
                    raise ValueError("invalid style")
            except Exception:
                # Never store provider exception text, request headers or raw responses.
                status, style = "fallback", None
            self._styles[cid] = style
            self._inference_events.append({"case_id": cid, "status": status,
                                           "elapsed_s": time.monotonic() - started})
        style = self._styles[cid]
        if style is None:
            return move
        return {**move, "message": {**message, "body": message.get("body", "") + "\n\n" + STYLES[style]}}

    def experiment_metrics(self):
        return {"inference_probe": {"calls": len(self._inference_events),
                                    "fallbacks": sum(e["status"] == "fallback" for e in self._inference_events),
                                    "events": list(self._inference_events)}}
