"""Set-based scoring with complete denominators. Labels never enter production prompts."""


def evaluate(manifest, records):
    by_key = {(r["example_id"], r["arm"]): r for r in records}
    result = {"review_status": manifest["review_status"], "evidence": "recorded fake responses only", "arms": {}}
    for arm in ("minimum", "direct", "grounded"):
        rows = [by_key.get((e["id"], arm)) for e in manifest["examples"]]
        available = [r for r in rows if r is not None]
        quality = sum(
            r is not None and r["action"] in e["admissible_actions"]
            for e, r in zip(manifest["examples"], rows, strict=True)
        )
        result["arms"][arm] = {
            "denominator": len(rows),
            "missing": len(rows) - len(available),
            "provisional_admissible_set_matches": quality,
            "structurally_admitted": sum(r["admitted"] for r in available),
            "grounded_model_departures": sum(r["grounded_departure"] for r in available),
            "fallbacks": sum(r["fallback"] for r in available),
            "calls": sum(r["calls"] for r in available),
            "charged_tokens": sum(r["charged_tokens"] for r in available),
            "unknown_usage_calls": sum(r["unknown_usage_calls"] for r in available),
            "latency_s": sum(r["latency_s"] for r in available),
            "held_out_denominator": sum(e["split"] == "held-out" for e in manifest["examples"]),
            "held_out_set_matches": sum(
                e["split"] == "held-out" and r is not None and r["action"] in e["admissible_actions"]
                for e, r in zip(manifest["examples"], rows, strict=True)
            ),
        }
    result["limitations"] = [
        "Independent review pending; provisional set matches are not validated decision quality.",
        "Fake latency and charged reservations do not measure real model speed, tokens or competence.",
        "No reactive negotiation outcomes or hosted inference were measured.",
    ]
    return result
