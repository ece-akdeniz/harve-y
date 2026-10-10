"""Concise human reports of public loop records, with explicit evidence gaps."""


def _cell(value):
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_report(body):
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
