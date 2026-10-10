"""Validate citations against stored original attempts, never narrative assertions."""


def validate_references(references, attempts):
    indexed = {a["attempt_id"]: a for a in attempts}
    for ref in references:
        if set(ref) - {"attempt_id", "supplier", "message_index"} or "attempt_id" not in ref:
            raise ValueError("invalid evidence reference")
        attempt = indexed.get(ref["attempt_id"])
        if attempt is None or attempt.get("status") == "pending":
            raise ValueError("evidence attempt unavailable")
        if "message_index" in ref and "supplier" not in ref:
            raise ValueError("message requires supplier")
        if "supplier" in ref:
            thread = attempt.get("threads", {}).get(ref["supplier"])
            if thread is None:
                raise ValueError("supplier evidence unavailable")
            if "message_index" in ref:
                messages = thread.get("messages", []) if isinstance(thread, dict) else thread
                index = ref["message_index"]
                if not isinstance(messages, list) or type(index) is not int or not 0 <= index < len(messages):
                    raise ValueError("message evidence unavailable")
    return references
