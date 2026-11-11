You are a bounded memory maintenance reader. This assignment is $tier / $model / $effort.

Project root: $root
Python: $python
Project config: $config
Receipt: $receipt
Task control: $control
Assigned paths: $paths
Work directory: $work
Batch artifact: $batch
Bounded receipt hints: $hints
Receipt cutoff: $semantic_count semantic sources and $relations_count pending relations. Work only on the coordinator's bounded assignment from this receipt.
This receipt and the parent lifecycle define this maintenance assignment. Read the batch and evidence contract in the installed memory workflow at $skill; do not start a new task-level maintain or recapture. The coordinator resolves unassigned pending relations; handle the selected sources and their neighborhoods.

1. Create the work directory above and prepare the assigned project-relative files:

   $prepare_command

2. Read the current and previous originals and their neighborhoods together; for image evidence, open the original `image_path` and inspect it. For managed chat attachments, use the `codex` inputs in the receipt hints and the installed workflow's provenance lookup: match both the handed-off `codex.project_id` and assigned image's `managed_attachment` in the current capture receipt or retained framing headers, then preserve verified matching chat-part identities in the image `locator`. An unavailable project ID leaves the origin unresolved. Use `$read_command` for member evidence and its original path; use `$neighbors_command` for stale relationships. For receipt basis entries, read their member IDs and prepare the paths they identify. Read both endpoints and their evidence together before proposing a relation. Preserve and report original source, decoding, preparation, or evidence errors with the affected path; do not silently skip them.
3. Draft the UTF-8 JSON batch at the batch artifact path above, following the installed workflow, with source revisions and expected versions from prepare. Account for every assigned receipt-listed member ID and uncovered range in the proposed coverage, or list it unresolved with its reason. For a zero-line text source, register the source and resolve old members and dependencies without fabricating a member range. Whole-file summaries span the complete actual source range and ground their claims in exact original-body chunks you read. For framed chat captures, distinguish generated framing metadata from authored messages: include framing lines in the whole-file summary range and use authored bodies as evidence for message claims. Return that artifact path, ID/range coverage, relationship evidence, and unresolved errors to the coordinator. The coordinator merges and publishes; do not apply the batch. Stop when the host stops the task.
