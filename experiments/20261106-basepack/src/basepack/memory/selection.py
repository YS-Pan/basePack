"""Sort final agent scores under a character budget; this is not host delivery."""

import json
import math


def select_scored(items: list[dict], budget: int) -> dict:
    if budget <= 0:
        raise ValueError("Memory content budget must be positive")
    for item in items:
        if isinstance(item["score"], bool) or not math.isfinite(item["score"]) or not 0 <= item["score"] <= 100:
            raise ValueError(f"Agent score must be finite and within 0–100 for {item['id']}")
        if not isinstance(item["knowledge_revision"], str) or not item["knowledge_revision"]:
            raise ValueError(f"knowledge_revision must identify the observed version for {item['id']}")
        if item.get("record_type", "member") not in ("member", "node", "semantic"):
            raise ValueError(f"Unsupported record_type for {item['id']}")
    selected, omitted = [], []
    identities, contents = set(), set()
    coverage = {}
    used = 0
    for item in sorted(items, key=lambda row: (-row["score"], row["id"])):
        reason = None
        record_type = item.get("record_type", "member")
        version = item["knowledge_revision"]
        identity = (record_type, item["id"], version)
        if record_type == "member":
            version = (version, item.get("source_version"), item["revision"])
            locator = json.dumps(item.get("locator"), sort_keys=True) if item["kind"] == "image" else None
            position = (item["start_line"], item["end_line"], locator)
            representation = (item["kind"], item.get("title", ""), item["text"])
            identity += (version, position, representation)
            content_key = (item["path"], version, position, representation)
        else:
            content_key = identity
        if identity in identities or content_key in contents:
            reason = "duplicate"
        if record_type == "member" and item["kind"] == "chunk":
            key = (item["path"], version)
            start, end = item["start_line"], item["end_line"]
            if any(left <= start and end <= right for left, right in coverage.get(key, [])):
                reason = "covered_original"
        if reason is None and used + len(item["text"]) > budget:
            reason = "budget"
        if reason:
            omitted.append({key: value for key, value in item.items() if key != "text"} | {"reason": reason})
            continue
        selected.append(item)
        used += len(item["text"])
        identities.add(identity)
        contents.add(content_key)
        if record_type == "member" and item["kind"] == "chunk":
            key = (item["path"], version)
            coverage.setdefault(key, []).append((item["start_line"], item["end_line"]))
    return {"items": selected, "text_characters": used, "budget": budget, "omitted": omitted}
