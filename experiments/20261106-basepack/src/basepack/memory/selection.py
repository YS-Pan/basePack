"""Sort agent scores and deliver content under an explicit character budget."""

import json
import math


def select_scored(items: list[dict], budget: int) -> dict:
    if budget <= 0:
        raise ValueError("Memory content budget must be positive")
    for item in items:
        if not math.isfinite(item["score"]):
            raise ValueError(f"Non-finite agent score for {item['id']}")
    selected, omitted = [], []
    identities, contents = set(), set()
    coverage = {}
    used = 0
    for item in sorted(items, key=lambda row: (-row["score"], row["id"])):
        reason = None
        version = (item.get("source_version"), item["revision"])
        locator = json.dumps(item.get("locator"), sort_keys=True) if item["kind"] == "image" else None
        position = (item["start_line"], item["end_line"], locator)
        representation = (item["kind"], item.get("title", ""), item["text"])
        identity = (item["id"], version, position, representation)
        content_key = (item["path"], version, position, representation)
        if identity in identities or content_key in contents:
            reason = "duplicate"
        if item["kind"] == "chunk":
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
        if item["kind"] == "chunk":
            key = (item["path"], version)
            coverage.setdefault(key, []).append((item["start_line"], item["end_line"]))
    return {"items": selected, "text_characters": used, "budget": budget, "omitted": omitted}
