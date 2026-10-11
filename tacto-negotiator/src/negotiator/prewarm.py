"""Pre-warm the data the first decision of every case loads lazily (decision-neutral).

With ten cases starting at once, the first `decide` of each case took 11-27 s (fast sim: up to 35 s)
while every later decision takes < 0.4 s: each agent loaded the data package (facts.json, release
overlay, a sha256 of every package file), built every supplier dossier from the SQLite database,
hashed the whole package tree again for its evidence context, and the ten threads fought for the GIL
while doing so. In the Live Final (8-minute wave, 60 s per message) that is half a round.

`prewarm()` does the shared work once, before the wave-case polling loop starts: the package
(`dossiers.load_package`, now cached per package files), every supplier dossier and its traits
(`dossiers.build_one`), facts.json, the package file scan of the evidence context
(`context.package_scan`), and the lazily imported modules (pypdf, openpyxl, claims, cost target ...).
`prewarm_case(agent, case)` builds what needs the case, per case and in parallel threads, before its
session is opened: the agent's evidence context (claim bank), supplier estimates, public traits and
trade-policy traits. Both are idempotent and degrade gracefully (log + continue) when data is missing.

Everything is the same object or value the lazy path would have loaded: the lazy loaders are not
bypassed, only called earlier. Trace rows: `prewarm {seconds, suppliers, cases, cache_sizes, ...}` and
`prewarm_case {case, seconds, suppliers, contexts, estimates, traits}`. The runtime key is
`PolicyConfig.prewarm` (default True; a policy with `"prewarm": false` skips both hooks).
"""

import asyncio
import importlib
import logging
import threading
import time

log = logging.getLogger("negotiator.prewarm")

# Fields a case listing (`/v1/cases`) carries that the opened session's case does not: the evidence
# context is keyed on the case content, so the pre-built context must use the opened session's shape.
LISTING_KEYS = frozenset({"hosted", "open", "seconds_left", "wave", "theme"})
# Modules the first decision imports lazily (the import lock serialises ten threads doing it at once).
LAZY_MODULES = (
    "pypdf", "openpyxl",
    "negotiator.claims", "negotiator.context", "negotiator.evidence", "negotiator.cost_target",
    "negotiator.bundle_volume", "negotiator.value_swap", "negotiator.trades", "negotiator.replies",
    "negotiator.ingestion", "negotiator.traits", "negotiator.dossiers", "negotiator.evaluator",
)
DATA_ERRORS = (OSError, ValueError, KeyError, TypeError, AttributeError, ZeroDivisionError, ImportError)

_LOCK = threading.RLock()
_WARMED: dict[tuple, dict] = {}  # package key -> summary of the completed package prewarm


def enabled(agent_or_policy) -> bool:
    """`PolicyConfig.prewarm` of the agent's policy (default True without a policy)."""
    policy = getattr(agent_or_policy, "policy", agent_or_policy)
    return getattr(policy, "prewarm", True) is not False


def listing_free(case: dict | None) -> dict | None:
    """The case without listing-only fields: what `open_session` returns as `case`."""
    if not isinstance(case, dict):
        return None
    return {k: v for k, v in case.items() if k not in LISTING_KEYS}


def cache_sizes() -> dict:
    out = {}
    try:
        from . import context, dossiers

        out.update(dossiers.cache_sizes())
        out.update(context.cache_sizes())
    except Exception:  # pragma: no cover - diagnostics only
        log.exception("prewarm: cache sizes unavailable")
    out["warmed_packages"] = len(_WARMED)
    return out


def _imports(summary: dict) -> None:
    done = 0
    for name in LAZY_MODULES:
        try:
            importlib.import_module(name)
            done += 1
        except ImportError as exc:  # optional reader missing: the lazy path fails the same way
            summary["errors"].append(f"import {name}: {exc}")
    summary["imports"] = done


def _supplier_ids(package, cases) -> list[str]:
    ids = set()
    try:
        if getattr(package, "db", None) is not None:
            ids.update(r["id"] for r in package.query("SELECT id FROM suppliers", limit=100_000))
    except DATA_ERRORS as exc:
        log.warning("prewarm: supplier table unavailable: %r", exc)
    for fact in (getattr(package, "facts", None) or {}).values():
        sup = fact.get("supplier") if isinstance(fact, dict) else None
        if isinstance(sup, str) and sup.startswith("sup:"):
            ids.add(sup)
    for case in cases or ():
        ids.update(s for s in (case.get("suppliers") or []) if isinstance(s, str))
    return sorted(ids)


def _warm_package(package, cases, summary: dict) -> None:
    from . import dossiers
    from .context import package_scan

    summary["facts"] = len(getattr(package, "facts", None) or {})
    try:
        summary["ids"] = len(package.ids("news:"))  # forces the citable-ID index over every table
    except DATA_ERRORS as exc:
        summary["errors"].append(f"ids: {exc}")
    built = 0
    for sid in _supplier_ids(package, cases):
        try:
            if dossiers.build_one(package, sid) is not None:
                built += 1
        except DATA_ERRORS as exc:
            summary["errors"].append(f"dossier {sid}: {exc}")
            log.warning("prewarm: dossier %s failed: %r; continuing", sid, exc)
    summary["suppliers"] = built
    docs = 0
    for prefix in ("ctr:", "doc:"):  # contract/letter texts the claim checks and dossiers read
        try:
            for ref in package.ids(prefix):
                try:
                    package.document(ref)
                    docs += 1
                except (OSError, ValueError):
                    pass  # the lazy path treats a missing document the same way
        except DATA_ERRORS as exc:
            summary["errors"].append(f"documents {prefix}: {exc}")
    summary["documents"] = docs
    try:
        files, _origins, _manifests = package_scan(package.root, package.release)
        summary["files"] = len(files)
    except DATA_ERRORS as exc:
        summary["errors"].append(f"scan: {exc}")
        log.warning("prewarm: package scan failed: %r; continuing", exc)


def prewarm(*, agent=None, cases=None, tracer=None, data_dir=None, release=None, force=False,
            quiet_cached=False) -> dict:
    """Load the data package, every supplier dossier, facts.json and the package scan once.

    Safe to call repeatedly (later calls return the cached summary with `cached: True` unless the
    package files changed or `force`). Never raises: a missing or broken package is logged and
    reported in `errors`; the lazy loaders then behave exactly as they would have anyway.
    `agent` (or its policy) supplies the `prewarm` runtime flag; `cases` adds their suppliers.
    `quiet_cached` suppresses the trace row when nothing had to be done (per-case callers)."""
    t0 = time.perf_counter()
    summary = {"seconds": 0.0, "suppliers": 0, "cases": len(cases or ()), "cache_sizes": {}, "errors": []}
    if tracer is None and agent is not None:
        tracer = getattr(agent, "tracer", None)
    if agent is not None and not enabled(agent):
        summary["disabled"] = True
        log.info("prewarm disabled by policy")
        return _finish(summary, t0, tracer)
    _imports(summary)
    try:
        from .dossiers import load_package, package_key

        package = load_package(data_dir, release)
        key = package_key(package.root, package.release)
    except DATA_ERRORS as exc:
        summary["errors"].append(f"package: {exc}")
        log.warning("prewarm: data package unavailable (%r); decisions load lazily as before", exc)
        return _finish(summary, t0, tracer)
    with _LOCK:
        done = _WARMED.get(key)
        if done is not None and not force:
            summary.update({k: done[k] for k in ("suppliers", "facts", "ids", "files", "documents") if k in done},
                           cached=True)
        else:
            try:
                _warm_package(package, cases, summary)
            except Exception as exc:  # never let the pre-warm stop a launch
                summary["errors"].append(f"warm: {exc!r}")
                log.exception("prewarm: package warm-up failed; continuing")
            _WARMED[key] = dict(summary)
    return _finish(summary, t0, None if quiet_cached and summary.get("cached") else tracer)


def _finish(summary: dict, t0: float, tracer) -> dict:
    summary["seconds"] = round(time.perf_counter() - t0, 3)
    summary["cache_sizes"] = cache_sizes()
    if tracer is not None:
        try:
            tracer.log("prewarm", **summary)
        except Exception:  # pragma: no cover - a tracer failure must not stop the launch
            log.exception("prewarm: trace failed")
    log.info("prewarm: %.2fs, %d suppliers, %s", summary["seconds"], summary["suppliers"], summary["cache_sizes"])
    return summary


def _evidence_wanted(agent, case) -> bool:
    """Mirror the first decision's gates for `EvidencePolicy.context_for`: single-supplier cases of the
    evidence case types, and RFQs with data claims. Otherwise the lazy path never builds the context."""
    ev = getattr(agent, "evidence", None)
    if ev is None:
        return False
    suppliers = case.get("suppliers") or []
    if case.get("type") in getattr(ev, "case_types", ()) and len(suppliers) == 1:
        return True
    pol = getattr(agent, "policy", None)
    return bool(pol and getattr(pol, "rfq_rival_offer", False) and case.get("type") == "rfq"
                and (getattr(pol, "rfq_data_claims", False) or getattr(pol, "rfq_data_claims_stack", False)))


def prewarm_case(agent, case, *, tracer=None) -> dict | None:
    """Build this agent's per-case caches for `case` before its session opens: evidence context,
    supplier estimates, public traits, trade-policy traits. `case` may be a listing entry (listing-only
    fields are dropped so the cached context matches the opened session's case). Idempotent per
    agent and case (the agent's own caches short-circuit); never raises. None when there is nothing
    to do (no case, pre-warming disabled)."""
    if agent is None or not enabled(agent):
        return None
    tracer = tracer if tracer is not None else getattr(agent, "tracer", None)
    # The package warm-up (idempotent): its own `prewarm` row only when this call does the work.
    prewarm(agent=agent, cases=[case] if isinstance(case, dict) else None, tracer=tracer, quiet_cached=True)
    case = listing_free(case)
    if not case or not case.get("case_id"):
        return None
    t0 = time.perf_counter()
    out = {"case": case["case_id"], "suppliers": len(case.get("suppliers") or []), "contexts": 0, "estimates": 0,
           "traits": 0, "errors": []}
    estimates_for = getattr(agent, "estimates_for", None)
    if callable(estimates_for):
        try:
            out["estimates"] = len(estimates_for(case) or {})
        except Exception as exc:
            out["errors"].append(f"estimates: {exc!r}")
            log.warning("prewarm %s: estimates failed: %r; continuing", case["case_id"], exc)
    public_traits = getattr(agent, "_public_traits", None)
    if callable(public_traits):
        for sid in case.get("suppliers") or []:
            try:
                public_traits(sid)
                out["traits"] += 1
            except Exception as exc:
                out["errors"].append(f"traits {sid}: {exc!r}")
                log.warning("prewarm %s: traits for %s failed: %r; continuing", case["case_id"], sid, exc)
    trades = getattr(agent, "trades", None)
    if trades is not None and callable(getattr(trades, "prepare", None)):
        try:
            trades.prepare(case)
        except Exception as exc:
            out["errors"].append(f"trades: {exc!r}")
            log.warning("prewarm %s: trade traits failed: %r; continuing", case["case_id"], exc)
    pol = getattr(agent, "policy", None)
    target = getattr(agent, "_target_supplier", None)
    if callable(target) and pol is not None and case.get("type") in (getattr(pol, "cost_target_types", ()) or ()):
        for sid in case.get("suppliers") or []:  # `_cost_target_move`'s dossier estimate, keyed (case, supplier)
            try:
                target(case, sid, {})
            except Exception as exc:
                out["errors"].append(f"target {sid}: {exc!r}")
                log.warning("prewarm %s: cost-target estimate for %s failed: %r; continuing", case["case_id"], sid, exc)
    if _evidence_wanted(agent, case):
        try:
            context = agent.evidence.context_for(case)
            out["contexts"] = 1
            out["claims"] = len(getattr(context, "candidates", ()) or ())
        except Exception as exc:  # the lazy path logs `evidence_fallback` and sends without claims
            out["errors"].append(f"evidence: {exc!r}")
            log.warning("prewarm %s: evidence context failed: %r; continuing", case["case_id"], exc)
    out["seconds"] = round(time.perf_counter() - t0, 3)
    if tracer is not None:
        try:
            tracer.log("prewarm_case", **out)
        except Exception:  # pragma: no cover
            log.exception("prewarm_case: trace failed")
    return out


async def prewarm_async(new_agent, *, tracer=None, cases=None) -> dict:
    """`prewarm()` in a worker thread for the async runners; `new_agent` (factory) supplies the flag."""
    probe = None
    if callable(new_agent):
        try:
            probe = new_agent()
        except Exception as exc:
            log.warning("prewarm: agent factory failed (%r); pre-warming the package anyway", exc)
    try:
        return await asyncio.to_thread(prewarm, agent=probe, cases=cases, tracer=tracer)
    except Exception as exc:  # pragma: no cover - prewarm() itself never raises
        log.exception("prewarm failed; continuing")
        return {"errors": [repr(exc)]}


async def prewarm_case_async(agent, case, *, tracer=None) -> dict | None:
    """`prewarm_case()` in a worker thread (one per case, so ten cases warm up in parallel)."""
    try:
        return await asyncio.to_thread(prewarm_case, agent, case, tracer=tracer)
    except Exception as exc:  # pragma: no cover - prewarm_case() itself never raises
        log.exception("prewarm_case failed; continuing")
        return {"errors": [repr(exc)]}
