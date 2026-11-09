"""Sort agent scores and deliver content under an explicit character budget."""

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
        content_key = (item["path"], item["revision"], item["start_line"],
                       item["end_line"], item["kind"], item["text"])
        if item["id"] in identities or content_key in contents:
            reason = "duplicate"
        if item["kind"] == "chunk":
            key = (item["path"], item["revision"])
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
        identities.add(item["id"])
        contents.add(content_key)
        if item["kind"] == "chunk":
            key = (item["path"], item["revision"])
            coverage.setdefault(key, []).append((item["start_line"], item["end_line"]))
    return {"items": selected, "text_characters": used, "budget": budget, "omitted": omitted}
