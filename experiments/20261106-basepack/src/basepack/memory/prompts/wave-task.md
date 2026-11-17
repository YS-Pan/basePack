You own this claimed finite maintenance task:

$task

Receipt hints: $hints
Work directory: $work

Follow the batch/evidence and private-source rules in $skill. Create the work directory and read the selected originals together using the following command. If no path was initially known, first use the relevant search/feedback clues to identify original files; replace the shell-quoted placeholder with those files. If originals cannot be identified, report the task unresolved rather than fabricating a path. `paths` is the only source-write scope for this task. `read_paths` and any other discovered originals are read-only evidence: never add them to draft sources or member paths unless they are also in `paths`; new required write scope belongs to a later wave.

$prepare_command

$prepare_inspection

On PowerShell, write multiline Python helpers to `.py` files in the task work directory and execute those files; do not use Bash heredocs or a standalone `PY` terminator.

Use `$search_command` for unresolved clues, `$read_command` for member evidence and `$neighbors_command` for relation history. For each image, open and inspect the original `image_path` rather than inferring content from metadata. For managed chat attachments, use the receipt hints and installed provenance lookup to match the project ID and managed attachment against the capture receipt or retained framing; preserve every verified chat-part identity in the image locator, and leave an unavailable origin unresolved. Resolve necessary basis and both relation endpoints with their original sources. Perform the task's actual reading, semantic chunking, summaries, relationships and ordinary repairs; own only its stated write targets. Keep unique facts, mandatory material, exact source versions, locators, privacy, and actual unread gaps. Keep ambiguous dependencies unresolved rather than fabricating evidence.

A full-file summary spans line 1 through the current EOF, including framing; a partial summary must state its `coverage_gaps`. For a text read with an explicit `--source-version`, supply the saved `--start-line` and `--end-line`.

For the same source revision, omit an entire dispositions/refinement field to retain it; an explicit list replaces that whole field and [] clears it. Before carrying old entries into an extended list, compare their pinned versions and applicability with prepare; changed evidence needs renewed judgment because the compiler fills current versions.

When you have read the available range and a fresh file/section summary covers it, submit a source-only `deferred_refinement` proposal for each pending gap that qualifies under the existing contract, binding the exact current member, knowledge revision and gap text. An adequate existing summary or this wave's coverage receipt alone does not persist that decision; do not rewrite the member, erase its gap or invent unavailable content. Unread ranges and gaps lacking qualifying coarse coverage remain unresolved. If the member must change, submit the member change first; after the publisher accepts it, prepare and defer its new version in a later wave.

Write one or more scoped proposal JSON drafts with `prepare:{path,file_sha256}` for the fixed reading package, plus separate coverage and errors JSON files in this work directory. For each assigned range, record represented, no-knowledge/duplicate, deferred refinement, or unresolved with reason. Record each actual failure in errors as a brief original error and its resolved or unresolved status; do not dump source stdout or replace failures with `[]` after fixing them. After submission keep every referenced file's bytes fixed; a repair uses a new file path and hash. Preserve full fixed references, do not publish, and return to the wave worker loop to submit them. A source-only registration is not semantic coverage. Do not start a separate maintenance run or a new team.
