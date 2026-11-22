"""Sort final agent scores under a character budget; this is not host delivery."""

import json
import math


def select_scored(items: list[dict], budget: int) -> dict:
    if budget <= 0:
        raise ValueError("Memory content budget must be positive")
    for item in items:
        if isinstance(item["score"], bool) or not math.isfinite(item["score"]) or not 0 <= item["score"] <= 100:
            raise ValueError(f"Agent score must be finite and within 0–100 for {item['id']}")
        record_type = item.get("record_type", "member")
        if record_type not in ("member", "node", "semantic", "source_version"):
            raise ValueError(f"Unsupported record_type for {item['id']}")
        revision = "revision" if record_type == "source_version" else "knowledge_revision"
        if not isinstance(item[revision], str) or not item[revision]:
            raise ValueError(f"{revision} must identify the observed version for {item['id']}")
        if record_type == "source_version" and not item["id"].startswith("source_version:"):
            raise ValueError("An original excerpt requires an exact source_version ID")
    selected, omitted = [], []
    identities, contents = set(), set()
    coverage = {}
    used = 0
    for item in sorted(items, key=lambda row: (-row["score"], row["id"])):
        reason = None
        record_type = item.get("record_type", "member")
        version = item["revision"] if record_type == "source_version" else item["knowledge_revision"]
        identity = (record_type, item["id"], version)
        located = record_type in {"member", "source_version"}
        if located:
            source_version = item["id"] if record_type == "source_version" else item.get("source_version")
            version = (item.get("knowledge_revision"), source_version, item["revision"])
            locator = item.get("locator")
            start_line, end_line = item["start_line"], item["end_line"]
            if item["kind"] == "image":
                position = (start_line, end_line, json.dumps(locator, sort_keys=True))
            else:
                # Without a column locator, both endpoint lines are complete.
                start_col, end_col = (0, math.inf) if locator is None else (locator["start_col"], locator["end_col"])
                position = ((start_line, start_col), (end_line, end_col))
            representation = (item["kind"], item.get("title", ""), item["text"])
            identity += (version, position, representation)
            content_key = (item["path"], version, position, representation)
        else:
            content_key = identity
        if identity in identities or content_key in contents:
            reason = "duplicate"
        if located and item["kind"] == "chunk":
            coverage_key = (item["path"], version)
            start, end = position
            if any(left <= start and end <= right for left, right in coverage.get(coverage_key, [])):
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
        if located and item["kind"] == "chunk":
            coverage.setdefault(coverage_key, []).append(position)
    return {"items": selected, "text_characters": used, "budget": budget, "omitted": omitted}
