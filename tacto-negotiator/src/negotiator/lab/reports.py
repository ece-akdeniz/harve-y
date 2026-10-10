"""Concise human reports of public loop records, with explicit evidence gaps."""


def _cell(value):
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _memory_citation(evidence):
    c = evidence["citation"]
    source = f"run {c['run_id']}" if c.get("run_id") else f"campaign {c.get('campaign_id')}"
    return (
        f"{source} / {c['attempt_id']} / {c['supplier']} / message {c['message_index']}"
        f" / {c['case_id']} / {c['session_id']}"
    )


def _memory_lessons(lessons, evidence):
    lines = []
    indexed = {item["evidence_id"]: item for item in evidence}
    if not lessons:
        return [
            "**Abstains:** Insufficient consistent evidence: require three distinct suppliers across two cases. "
            "Observed offers alone do not teach a preference; conflicting statements suppress lessons."
        ]
    for lesson in lessons:
        support = [indexed[key] for key in lesson["evidence_ids"] if key in indexed]
        suppliers = len({item["citation"]["supplier"] for item in support})
        cases = len({item["citation"]["case_id"] for item in support})
        field = lesson["field"].replace("_", " ")
        lines.append(
            f"- **Candidate:** {field} — prefer {lesson['direction']}; {suppliers} suppliers, {cases} cases, "
            f"{len(lesson['evidence_ids'])} supporting citations. Held-out evaluation required."
        )
        for item in support[:3]:
            lines.append(f"  - {_cell(_memory_citation(item))}")
        if len(support) > 3:
            lines.append(f"  - {len(support) - 3} more citations; inspect the complete JSON evidence.")
    return lines


def _memory_snapshot(snapshot):
    lines = [f"### Snapshot {snapshot['snapshot_id']}",
             f"**Scope:** {_cell(snapshot['arena_url'])} / {_cell(snapshot['environment'])}",
             "**Status:** Candidate snapshot; no score or promotion claim."
             if snapshot["lessons"] else "**Status:** Abstains; no qualified lessons."]
    for name in ("cases", "suppliers", "sessions"):
        values = snapshot["source_" + name]
        lines.append(f"**Discovery {name}:** " + (", ".join(_cell(value) for value in values) or "none"))
    lines.append(
        f"**Frozen cohort:** {len(snapshot['source_suppliers'])} suppliers / {len(snapshot['source_cases'])} cases / "
        f"{len(snapshot['source_sessions'])} sessions / {len(snapshot['evidence'])} evidence rows"
    )
    lines.extend(_memory_lessons(snapshot["lessons"], snapshot["evidence"]))
    return lines


def _memory_report(body):
    if "memory-snapshots" in body:
        snapshots = body["memory-snapshots"]
        lines = [f"## Immutable memory snapshots ({len(snapshots)})"]
        if not snapshots:
            lines.append("No frozen snapshots. Build an explicitly scoped discovery candidate with the lab CLI.")
        for snapshot in snapshots:
            lines.extend(_memory_snapshot(snapshot))
    elif "snapshot_id" in body:
        lines = _memory_snapshot(body)
    elif "observations" in body and "coverage" in body:
        coverage, observations = body["coverage"], body["observations"]
        lines = ["## Supplier memory graph",
                 f"**Coverage:** {coverage['session_count']} original sessions / "
                 f"{coverage['supplier_count']} suppliers / {coverage['case_count']} cases / "
                 f"{len(observations)} observations", "### Candidate general lessons"]
        lines.extend(_memory_lessons(body["lessons"], observations))
        for conflict in body["conflicts"]:
            lines.append(
                f"**Conflict — abstains:** {conflict['field'].replace('_', ' ')} / "
                f"{_cell(conflict['arena_url'])} / {conflict['environment']} / "
                f"{len(conflict['evidence_ids'])} opposing statement citations"
            )
        lines.extend(["### Supplier observation history",
                      f"Showing {min(25, len(observations))} of {len(observations)} observations; "
                      "use --format json for complete evidence. Message indexes are zero-based.",
                      "| Kind / field / value | Scope | Source citation |", "|---|---|---|"])
        for observation in observations[:25]:
            c = observation["citation"]
            value = observation["direction"] if observation["direction"] is not None else observation["value"]
            description = f"{observation['kind']} / {observation['field']} / {value}".replace("_", " ")
            lines.append(
                f"| {_cell(description)} | {_cell(c['arena_url'])} / {_cell(c['environment'])} "
                f"| {_cell(_memory_citation(observation))} |"
            )
    else:
        return None
    return "\n\n".join(lines).replace("\n\n|", "\n|") + "\n"


def markdown_report(body):
    memory = _memory_report(body)
    if memory is not None:
        return memory
    lines = []
    for key in (
        "checkpoint_id",
        "campaign_id",
        "suite_id",
        "family_id",
        "status",
        "generation",
        "destination",
        "execution_status",
    ):
        if key in body:
            lines.append(f"**{key.replace('_', ' ').title()}:** {_cell(body[key])}")
    if body.get("completion"):
        lines.append(f"**Completion:** {_cell(body['completion'].get('status'))}")
    if body.get("next_action"):
        lines.append(f"**Next action:** {body['next_action']}")
    if body.get("blocking_attempts"):
        lines.append("**Blocking attempts:** " + ", ".join(body["blocking_attempts"]))
    evaluation = body.get("evaluation", body.get("completion", {}).get("evaluation", body))
    if "eligible" in evaluation:
        lines.append(f"**Eligible:** {evaluation['eligible']}")
    if evaluation.get("gates"):
        lines += ["", "| Gate | Passed | Evidence |", "|---|---|---|"]
        for gate in evaluation["gates"]:
            lines.append(f"| {_cell(gate['id'])} | {_cell(gate['passed'])} | {_cell(gate.get('detail'))} |")
    if evaluation.get("cases"):
        lines += [
            "",
            "| Case | Baseline mean | Candidate mean | Gain | Baseline spread | Candidate spread |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for case in evaluation["cases"]:
            values = (
                case["case_id"],
                case["baseline"].get("mean"),
                case["candidate"].get("mean"),
                case.get("gain"),
                case["baseline"].get("spread"),
                case["candidate"].get("spread"),
            )
            lines.append("| " + " | ".join(_cell(value) for value in values) + " |")
    if evaluation.get("repeats"):
        lines += ["", "| Repeat | Baseline | Candidate | Gain |", "|---|---:|---:|---:|"]
        for repeat in evaluation["repeats"]:
            lines.append(
                "| " + " | ".join(_cell(repeat.get(k)) for k in ("repeat", "baseline", "candidate", "gain")) + " |"
            )
    if evaluation.get("evidence_gaps"):
        lines.append("**Evidence gaps:** " + ", ".join(evaluation["evidence_gaps"]))
    attempts = body.get("attempts", [body["attempt"]] if "attempt" in body else [])
    if attempts:
        lines += [
            "",
            "| Attempt | Case | Arm | Status | Score | Timeouts | Session |",
            "|---|---|---|---|---:|---:|---|",
        ]
        for attempt in attempts:
            lines.append(
                "| "
                + " | ".join(
                    _cell(attempt.get(k))
                    for k in ("attempt_id", "case_id", "arm", "status", "score", "timeouts", "session_id")
                )
                + " |"
            )
            result = attempt.get("result", {})
            for field in ("deal", "must_haves_ok", "cost_breakdown", "terms", "term_sheets"):
                if field in result:
                    lines.append(f"**{field.replace('_', ' ')}:** {_cell(result[field])}")
            if attempt.get("error"):
                lines.append(f"**Failure:** {_cell(attempt['error'])}")
            for supplier, thread in attempt.get("threads", {}).items():
                messages = thread if isinstance(thread, list) else thread.get("messages", thread.get("events", []))
                for index, message in enumerate(messages):
                    if not isinstance(message, dict):
                        continue
                    selected = body.get("selection", {}).get("message_index")
                    reference_index = selected if selected is not None else index
                    lines.append(f"\n**Message reference:** `{attempt['attempt_id']}/{supplier}/{reference_index}`")
                    lines.append(str(message.get("body", message.get("text", ""))))
                    for field in ("refs", "term_sheets", "terms", "cost_breakdown"):
                        if field in message:
                            lines.append(f"**{field}:** {_cell(message[field])}")
    if body.get("config"):
        lines.append(
            "**Configuration:** " + ", ".join(f"{key}={_cell(value)}" for key, value in body["config"].items())
        )
    for key in ("commit", "runner", "published", "lock_sha256", "description", "author", "ref", "max_sessions"):
        if key in body:
            lines.append(f"**{key.replace('_', ' ').title()}:** {_cell(body[key])}")
    for key in ("history", "findings", "suites", "checkpoints", "families", "recommended"):
        if key in body and isinstance(body[key], list):
            lines.append(f"**{key.title()}:** {len(body[key])}")
            lines.extend(
                "- "
                + ", ".join(
                    f"{k}: {_cell(v)}"
                    for k, v in entry.items()
                    if k
                    in (
                        "suite_id",
                        "checkpoint_id",
                        "family_id",
                        "finding_id",
                        "campaign_id",
                        "action",
                        "observation",
                        "next_test",
                    )
                )
                for entry in body[key]
            )
    if not lines:
        lines.append("**Record:** " + ", ".join(f"{key}: {_cell(value)}" for key, value in body.items()))
    return "\n\n".join(lines).replace("\n\n|", "\n|") + "\n"
