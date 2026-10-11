"""Prepare or execute ONE explicitly authorized hosted V2 stage through the existing Lab.

Default mode is local preparation only. D01 -> D02 -> P10 requires a fresh evidence review
and authorization for each stage. No session/inference/publication occurs while preparing.
"""

import argparse
import base64
import hashlib
import json
import math
import os
import time
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

import httpx
from arena_kit.cli import load_env
from arena_kit.cost import must_haves_ok

from negotiator.lab.lifecycle import PublicationJournal, bounded_read, reconcile_publication, upload_once
from negotiator.lab.publish import _atomic_file, save_snapshot
from negotiator.lab.runner import capture_provenance, plan_run, replay_url, run_experiment, sanitize
from negotiator.lab.transport import JournaledArena
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.factory import online_lab_agent

from .run_adaptive_milestone import CONFIG, PER_CALL_TOKENS, OfflineAllowance
from .run_adaptive_milestone import plan as offline_plan
from .run_lab_local import PROJECT

STAGES = {"D01": ("sandbox", 18, "1.00", None),
          "D02": ("sandbox", 36, "2.00", "D01"),
          "P10": ("practice", 18, "1.00", "D02")}


def verify_model_access():
    if not os.environ.get("LLM_API_KEY"):
        raise ValueError("LLM_API_KEY missing")
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        response = client.get(CONFIG.base_url + "/models/" + CONFIG.model_id,
                              headers={"Authorization": "Bearer " + os.environ["LLM_API_KEY"]})
        response.raise_for_status()
        if response.json().get("id") != CONFIG.model_id:
            raise ValueError("authorized model metadata mismatch")


def verify_lab_access(url):
    if os.environ.get("LAB_URL", "").rstrip("/") != url.rstrip("/") or not os.environ.get("LAB_UPLOAD_TOKEN"):
        raise ValueError("Lab credentials/destination differ from the explicit allowance")
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        response = client.get(url.rstrip("/") + "/api/runs",
                              headers={"Authorization": "Bearer " + os.environ["LAB_UPLOAD_TOKEN"]})
        response.raise_for_status()
        if not isinstance(response.json().get("runs"), list):
            raise ValueError("normal Lab listing unavailable")


def publication_state_path(output, run_id):
    directory = Path(output) / "publication-state"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory / f"{run_id}.json"


def publish_verified(run, url, output, *, transport=None, timeout=30):
    """Freeze, publish once, then verify by read-only item/listing retrieval."""
    journal = PublicationJournal(publication_state_path(output, run.run_id))
    terminal_complete = (run.environment == "simulator" or
                         journal.state["evidence_collection"].get("status") == "complete")
    journal.prepare(run, url, terminal_complete=terminal_complete)
    token = os.environ.get("LAB_UPLOAD_TOKEN", "")
    if journal.state["publication"]["write_attempted"]:
        proof_result = reconcile_publication(journal, token=token, timeout=min(timeout, 10), transport=transport)
    else:
        result = upload_once(journal, token=token, timeout=timeout, transport=transport)
        if result["status"] == "rejected":
            raise ValueError("Lab rejected publication; preserve the frozen payload")
        proof_result = reconcile_publication(journal, token=token, timeout=min(timeout, 10), transport=transport)
    if proof_result["status"] != "verified":
        raise ValueError("Lab publication is not verified; preserve the frozen payload and reconcile read-only")
    proof = {"lab_url": url, "run_id": run.run_id, "retrieval_verified": True,
             "listing_verified": True, "payload_sha256": journal.state["publication"]["payload_sha256"],
             "run": journal.state["publication"]["payload"]}
    _atomic_file(output / ("lab-proof-" + run.run_id + ".json"), json.dumps(proof, indent=2))
    return proof


def dataset_for(case):
    if case["case_id"] not in {"case:D01", "case:D02", "case:P10"} or len(case["parts"]) != 1:
        raise ValueError("unsupported hosted case/part count")
    # Baseline is a legal buyer-plan package, not a simulator-specific bargaining rule.
    buyer = case["buyer"]
    preferred = {"unit_price": buyer.get("current_unit_price") or buyer["fallback_unit_price"],
                 "payment_days": buyer["reference_payment_days"], "lead_time_days": buyer["need_lead_time_days"],
                 "incoterm": "DAP", "contract_months": round(12 * buyer["horizon_years"]),
                 "volume_per_year": buyer["need_per_year"]}
    terms = {}
    for field in case["negotiable"]:
        choices = case["term_options"].get(field)
        value = preferred.get(field)
        terms[field] = value if not choices or value in choices else choices[0]
    if not must_haves_ok(case, terms):
        raise ValueError("buyer-plan baseline violates must-haves; explicit case support needed")
    return {"case": case, "price_unit": 1, "supplier_messages": [], "candidate_terms": [terms],
            "price_basis_source": "official case briefing: EUR per unit; single part",
            "estimate_limit": "supplier full-cost estimates unavailable; relationship component explicitly unestimated"}


def prior_review(path, stage):
    predecessor = STAGES[stage][3]
    if predecessor is None:
        return None  # Explicit user priority: D01 is the first genuine hosted validation.
    if path is None:
        raise ValueError("prior stage actual transcript and blockers must be reviewed first")
    review = json.loads(path.read_text())
    required = {"stage": predecessor, "transcript_reviewed": True, "blocking_issues_resolved": True,
                "genuine_hosted_model": True, "lab_retrieval_verified": True}
    if any(review.get(key) != value for key, value in required.items()):
        raise ValueError("prior stage actual transcript and blockers must be reviewed first")
    proofs = []
    for artifact in review.get("artifacts", []):
        p = Path(artifact["path"])
        if hashlib.sha256(p.read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError("prior reviewed artifact changed")
        content = json.loads(p.read_text())
        if isinstance(content, dict) and content.get("retrieval_verified") is True and "run" in content:
            proofs.append(content)
    if not review.get("artifacts"):
        raise ValueError("review requires actual original evidence artifacts")
    adaptive = [proof["run"] for proof in proofs if proof["run"].get("config", {}).get("arm") == "adaptive"
                or proof["run"].get("environment") in {"sandbox", "practice"}]
    if len(adaptive) != 1:
        raise ValueError("review requires exactly one actual adaptive predecessor Lab retrieval proof")
    run = adaptive[0]
    expected_case = "case:P10" if predecessor == "offline" else "case:" + predecessor
    if run.get("status") != "completed" or run.get("cases") != [expected_case]:
        raise ValueError("predecessor outcome/case does not match the execution order")
    attempt = run["attempts"][0]
    metrics = attempt["result"].get("agent_metrics", {})
    if metrics.get("model") != CONFIG.model_id or not any(
            d.get("proposal_admitted") is True and d.get("interpretation_admitted") is True
            for d in metrics.get("decisions", [])):
        raise ValueError("predecessor requires admitted genuine model interpretation and proposals")
    evidence = attempt["result"].get("agent_evidence", {})
    if predecessor == "offline":
        validation = evidence.get("validation_evidence", {})
        report = json.loads(validation.get("interpretation_report_json", "{}"))
        if report.get("semantic_correct", 0) < 12 or run.get("environment") != "simulator":
            raise ValueError("offline semantic validation and official simulator evidence required")
    else:
        terminal = json.loads(evidence.get("terminal_json", "{}"))
        if run.get("environment") != "sandbox" or terminal.get("state", {}).get("status") != "ended":
            raise ValueError("original ended sandbox terminal evidence required")
    return semantic_hash(review)


def plan(stage, dataset, lab_url, prior_review_hash=None):
    environment, calls, dollars, predecessor = STAGES[stage]
    return {"authorized": False, "token_accounting_confirmed": False,
            "stage": stage, "case": "case:" + stage, "case_hash": semantic_hash(dataset["case"]),
            "dataset_hash": semantic_hash(dataset), "environment": environment,
            "arena_url": "https://arena.tacto.ai", "online_sessions": 1, "remote_writes": 1,
            "lab_url": lab_url, "model_config": asdict(CONFIG), "model_id": CONFIG.model_id,
            "strategy": "bounded-proposal-v3+deterministic-evidence-copy-v1",
            "max_calls": calls, "max_usd": dollars,
            "max_total_reserved_tokens": calls * PER_CALL_TOKENS,
            "max_output_tokens": CONFIG.max_output_tokens, "retries": 0, "automatic_reruns": 0,
            "source_sha256": offline_plan()["source_sha256"], "prior_stage": predecessor,
            "prior_review_hash": prior_review_hash, "offline_verification": predecessor is not None,
            "direct_sandbox_validation": stage == "D01", "remote_lab_verified": True,
            "token_accounting": offline_plan()["token_accounting"],
            "supplier_estimates": dataset.get("estimate_limit"),
            "review_required": "review this actual D01 transcript before D02" if stage == "D01" else
            "complete predecessor transcript, semantic quality, fallbacks, economics and blockers"}


class SingleSessionArena(JournaledArena):
    def __init__(self, path, case_id, **kwargs):
        super().__init__(path, **kwargs)
        self.case_id = case_id

    def _call(self, method, path, body=None, params=None, raw=False):
        if method == "POST" and path == "/sessions":
            attempted = any(r.get("rec") == "intent" and r.get("path") == "/sessions"
                            for r in self.journal.records)
            if body != {"case_id": self.case_id} or attempted or self.journal.pending():
                raise ValueError("one exact authorized session only; no reopen or retry")
        elif method == "POST":
            owned = self.journal.session_for(self.case_id)
            case = self.journal.case_file(self.case_id) or {}
            permitted = {f"/sessions/{owned}/threads/{supplier}/messages" for supplier in case.get("suppliers", [])}
            if not owned or path not in permitted:
                raise ValueError("submission is outside the authorized owned session/supplier endpoints")
        return super()._call(method, path, body, params, raw)


def capture_terminal_evidence(run, client, agent, output, *, wait_seconds=300, request_timeout=10,
                              poll_interval=2, clock=time.monotonic, sleeper=time.sleep):
    """Durably collect all owned terminal evidence under overall and per-read deadlines."""
    attempt = run.attempts[0]
    if not attempt.session_id:
        raise ValueError("missing terminal evidence: no owned session identity")
    journal = PublicationJournal(publication_state_path(output, run.run_id))
    deadline = clock() + max(0, wait_seconds)
    session_id = attempt.session_id
    evidence_path = output / "terminal-evidence" / f"{session_id}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if evidence_path.is_file():
        collected = json.loads(evidence_path.read_text())
        if collected.get("schema_version") != 1 or collected.get("session_id") != session_id:
            raise ValueError("local terminal evidence belongs to another session; recovery is blocked")
        collected["status"] = "collecting"
        collected.pop("collection_error", None)
    else:
        collected = {"schema_version": 1, "session_id": session_id, "status": "collecting",
                     "session": None, "threads": {}, "attachments": {}}
    _atomic_file(evidence_path, json.dumps(collected, allow_nan=False, indent=2))
    journal.mark_collection("in_progress", session_id=session_id, terminal_path=evidence_path)

    def read(read_fn):
        last_error = None
        while clock() < deadline:
            try:
                return bounded_read(read_fn, deadline=deadline, request_timeout=request_timeout, clock=clock)
            except TimeoutError:
                raise
            except Exception as error:  # transient owned GET failure; retry only the read
                last_error = error
                remaining = deadline - clock()
                if remaining <= 0:
                    break
                sleeper(min(poll_interval, remaining))
        if last_error:
            raise TimeoutError("terminal evidence collection deadline exhausted after read failures") from None
        raise TimeoutError("terminal evidence collection deadline exhausted")

    try:
        while True:
            state = read(lambda: client.session(session_id))
            if state.get("session_id") != session_id or state.get("status") not in {"open", "ended"}:
                raise ValueError("terminal evidence identity/status mismatch")
            collected["session"] = state
            _atomic_file(evidence_path, json.dumps(collected, allow_nan=False, indent=2))
            if state["status"] == "ended":
                break
            remaining = deadline - clock()
            if remaining <= 0:
                raise TimeoutError("terminal evidence collection deadline exhausted before terminality")
            sleeper(min(poll_interval, remaining))

        if not isinstance(state.get("result"), dict) or not isinstance(state.get("threads"), dict):
            raise ValueError("terminal evidence is incomplete")
        thread_ids = list(state["threads"])
        if not thread_ids or len(thread_ids) > 100:
            raise ValueError("terminal evidence thread manifest is incomplete or over limit")
        for supplier in thread_ids:
            thread = read(lambda supplier=supplier: client.thread(session_id, supplier))
            if not isinstance(thread, dict) or not isinstance(thread.get("messages"), list):
                raise ValueError("terminal thread evidence is incomplete")
            collected["threads"][supplier] = thread
            _atomic_file(evidence_path, json.dumps(collected, allow_nan=False, indent=2))
            for message in thread["messages"]:
                for attachment in message.get("attachments", []):
                    attachment_id = attachment.get("attachment_id")
                    if not isinstance(attachment_id, str) or not attachment_id:
                        raise ValueError("terminal attachment identity missing")
                    if attachment_id not in collected["attachments"]:
                        content = read(lambda attachment_id=attachment_id: client.attachment(session_id, attachment_id))
                        collected["attachments"][attachment_id] = base64.b64encode(content).decode("ascii")
                    _atomic_file(evidence_path, json.dumps(collected, allow_nan=False, indent=2))

        attempt.threads = sanitize(collected["threads"], budget=300000)
        if attempt.threads != collected["threads"]:
            raise ValueError("complete terminal thread evidence exceeds the local evidence bounds")
        attempt.replay_url = replay_url(state.get("replay_url"), run.arena_url)
        attempt.rounds = state.get("rounds") if type(state.get("rounds")) is int else attempt.rounds
        attempt.timeouts = sum(len(t.get("timeouts", [])) if isinstance(t.get("timeouts", []), list)
                               else max(0, int(t.get("timeouts", 0) or 0)) for t in attempt.threads.values())
        for _supplier, thread in attempt.threads.items():
            for message in thread["messages"]:
                for attachment in message.get("attachments", []):
                    attachment_id = attachment["attachment_id"]
                    if attachment_id in collected["attachments"]:
                        agent.observe_lab_attachment(attachment_id,
                            base64.b64decode(collected["attachments"][attachment_id]))
        agent.observe_lab_terminal(state)
        agent.observe_lab_outcome(state["result"], attempt.threads)
        attempt.result.update(state["result"])
        attempt.result["agent_evidence"] = agent.experiment_evidence()
        if attempt.status == "running":
            score = state["result"].get("score")
            if score is not None and (isinstance(score, bool) or not isinstance(score, (int, float))
                                      or not math.isfinite(score) or not 0 <= score <= 1):
                attempt.status, attempt.error = "failed", "invalid authoritative terminal score"
            else:
                attempt.score, attempt.status = float(score) if score is not None else None, "completed"
        if run.status == "running":
            run.status = "completed" if all(a.status == "completed" for a in run.attempts) else "failed"
        collected["status"] = "complete"
        _atomic_file(evidence_path, json.dumps(collected, allow_nan=False, indent=2))
        journal.mark_collection("complete", session_id=session_id, terminal_path=evidence_path)
        run.revision += 1
        save_snapshot(run, output / "runs")
        return evidence_path
    except KeyboardInterrupt:
        collected["status"] = "interrupted"
        _atomic_file(evidence_path, json.dumps(collected, allow_nan=False, indent=2))
        journal.mark_collection("missing", session_id=session_id, error="interrupted", terminal_path=evidence_path)
        raise
    except Exception as error:
        collected["status"] = "missing"
        collected["collection_error"] = type(error).__name__
        _atomic_file(evidence_path, json.dumps(collected, allow_nan=False, indent=2))
        journal.mark_collection(
            "missing", session_id=session_id, error=type(error).__name__, terminal_path=evidence_path
        )
        raise ValueError("complete terminal evidence unavailable; publication is blocked") from error


def capture_failed_terminal(run, client, agent, output, *, wait_seconds=300, **kwargs):
    """Compatibility name retained for prior local callers; captures all outcomes."""
    return capture_terminal_evidence(run, client, agent, output, wait_seconds=wait_seconds, **kwargs)


def execute(output, authorization, stage, dataset, lab_url, review_path=None):
    review_hash = prior_review(review_path, stage)
    expected = plan(stage, dataset, lab_url, review_hash)
    approved = json.loads(authorization.read_text())
    if approved != {**expected, "authorized": True, "token_accounting_confirmed": True}:
        raise ValueError("exact source/case/session/inference/Lab-write authorization required")
    load_env()
    if not os.environ.get("LLM_API_KEY") or not os.environ.get("ARENA_API_KEY"):
        raise ValueError("hosted credentials missing")
    if os.environ.get("ARENA_URL", "https://arena.tacto.ai").rstrip("/") != approved["arena_url"]:
        raise ValueError("Arena destination differs from explicit authorization")
    verify_lab_access(lab_url)
    verify_model_access()
    if output.exists():
        raise ValueError("fresh output required; no automatic restart/rerun")
    output.mkdir(parents=True, mode=0o700)
    marker = authorization.with_name(authorization.name + ".consumed")
    with os.fdopen(os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        stream.write(semantic_hash(approved))
        stream.flush()
        os.fsync(stream.fileno())
    _atomic_file(output / "approved-plan.json", json.dumps(approved, indent=2))
    _atomic_file(output / "dataset.json", json.dumps(dataset, indent=2))
    allowance = OfflineAllowance(output, max_calls=approved["max_calls"], max_usd=Decimal(approved["max_usd"]))
    client = SingleSessionArena(output / "arena-journal.jsonl", approved["case"],
                                base_url=approved["arena_url"], api_key=os.environ["ARENA_API_KEY"], timeout=180)
    try:
        me = client.me()
        cases = client.cases(approved["environment"])
        actual = next((case for case in cases if case["case_id"] == approved["case"]), None)
        if me.get("status") != "active" or actual != dataset["case"]:
            raise ValueError("current permissions/case differ from reviewed readiness")
        if stage == "P10" and (actual.get("hosted") is not True or me.get("practice", {}).get("left", 0) < 1):
            raise ValueError("practice case/quota unavailable")
        if client.journal.pending():
            raise ValueError("unresolved submission; read-only reconciliation required")
        _atomic_file(output / "preflight.json", json.dumps({"me": me, "case": actual}, indent=2))
        agent = online_lab_agent(dataset_path=output / "dataset.json", trace_root=output / "traces",
                                 transport=allowance, model_config=CONFIG, execution_allowance=approved)
        provenance, patch = capture_provenance(PROJECT, data_dir=output, allow_dirty=True)
        run = plan_run(name="V2 hosted " + stage, author="authorized-v2-validation",
            hypothesis="Real citation-grounded adaptive proposals negotiate using complete official observations.",
            agent="negotiator.v2.factory:online_lab_agent", config={"execution_plan_json": json.dumps(approved)},
            cases=[approved["case"]], repetitions=1, max_sessions=1, environment=approved["environment"],
            arena_url=approved["arena_url"], provenance=provenance)
        final = run_experiment(run, output / "runs", client, lambda: agent, patch=patch)
        # Both completed and failed agent executions require authoritative terminal
        # Arena evidence before the immutable Lab payload can be prepared.
        capture_terminal_evidence(final, client, agent, output)
        # Publish original failed attempts too. A failure never authorizes a replacement session.
        publish_verified(final, lab_url, output)
        if final.status != "completed" or allowance.stopped or client.journal.pending():
            raise ValueError("hosted stage failed or uncertain; review original evidence before proceeding")
        _atomic_file(output / "review-required.json", json.dumps({"stage": stage,
            "transcript_reviewed": False, "blocking_issues_resolved": False, "genuine_hosted_model": True,
            "lab_retrieval_verified": True, "artifacts": []}, indent=2))
    finally:
        client.http.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--lab-url", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prior-review", type=Path)
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text())
    environment = STAGES[args.stage][0]
    case = next(c for c in metadata["cases?set=" + environment] if c["case_id"] == "case:" + args.stage)
    dataset = dataset_for(case)
    review_hash = prior_review(args.prior_review, args.stage) if args.prior_review else None
    if args.authorization:
        if STAGES[args.stage][3] is not None and not args.prior_review:
            raise ValueError("prior actual transcript review required before execution")
        execute(args.out, args.authorization, args.stage, dataset, args.lab_url, args.prior_review)
    else:
        args.out.mkdir(parents=True, exist_ok=True)
        _atomic_file(args.out / "dataset.json", json.dumps(dataset, indent=2))
        _atomic_file(args.out / "authorization-template.json", json.dumps(
            plan(args.stage, dataset, args.lab_url, review_hash), indent=2))
        print("Prepared " + args.stage + "; inference=0; sessions=0; Lab writes=0; explicit approval required")


if __name__ == "__main__":
    main()
