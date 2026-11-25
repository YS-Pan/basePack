You own this claimed finite maintenance task:

$task

Receipt hints: $hints
Fixed maintenance receipt: $receipt
Work directory: $work

When a retained or discovery gap affects the assigned work, read the matching entries from the fixed maintenance receipt.

Follow the batch/evidence and private-source rules in $skill. Create the work directory and read the selected originals together using the following command. If no path was initially known, first use the relevant search/feedback clues to identify original files; replace the shell-quoted placeholder with those files. If originals cannot be identified, report the task unresolved rather than fabricating a path. `paths` authorizes source and member writes at those paths. `write_targets` coordinates shared node/edge ownership; an empty list does not make those source members read-only. `read_paths` and any other discovered originals are read-only evidence: never add them to draft sources or member paths unless they are also in `paths`; new required write scope belongs to a later wave.

$prepare_command

$prepare_inspection

When `graph_candidate` is present, read the two exact `graph_endpoints` originals at the assigned ranges, including locator columns. Check the stated versions against fixed prepare. Judge the meaning, direction, applicability and future retrieval use from the originals. A shared input supports the common-input fact. Claims of derivation or a shared result need original evidence for those claims.

Save `graph_review` inside the coverage JSON with `candidate`, `outcome`, `reason`, and `read` containing both exact `{id,knowledge_revision,source_version}` triples. Choose one outcome after reading both originals.

- `proposed` with one draft when a verified relationship has a concrete reuse task. Name that task in `reason`. The draft contains `prepare`, `sources: []` and one entry in `edges`. Use the exact member IDs in `in` and `out` and pin each in `endpoint_versions` as `{id,knowledge_revision}`. Cite the supporting member IDs in `evidence` or cite exact locations within the assigned ranges in `basis`. Use the relation `type` and direction from the skill, concise `text`, applicable `conditions`, and a specific English `label` for `other`.
- `nonpersistent` without a draft when a verified relationship is useful only for this reading. Describe it, its conditions and the limited use in `reason` so the result can be returned with the reading.
- `no_relation` without a draft when the read evidence establishes no applicable relationship in the reviewed scope. Record that scope and the reason.

If either original is unavailable or the evidence leaves the relationship or its applicability unresolved, submit `--failed` with the missing evidence and the exact versions actually read.

When `outcome_candidate` is present, inspect the pinned chat from `start_line` and any fixed previous closure. Find one adopted or executed outcome. Read the deliverable, its editable or generating source, the exact inputs and the adoption or execution record. Plans and co-occurrences give leads. Check current edges, then put all evidenced new hops in one draft with `sources: []`. Use `prepare` to get `sources[].revision` for any additional paths. Run the pinned preparation command with all chat and evidence paths, and put each observed raw revision in `--expected-revisions`. Cite read-only snapshots by `source_version` and exact location.

Record `outcome_review` in coverage with `candidate` (the ID), `revision`, `source_version`, `checked_through` (last consecutively examined chat line), `status`, and `reason`. Choose `continue` when the budget or another lead leaves unexamined lines. Carry forward missing proof from earlier lines. At the end choose `exhausted` if finished or `blocked` with the missing evidence and a `breakpoint` line to return to. In `missing_paths`, map each known required project path to the accepted `source_version` you checked or `null` when none exists. One outcome is enough per task. Report a failed read or authoring operation as `--failed` with its error and available evidence.

On PowerShell, write multiline Python helpers to `.py` files in the task work directory and execute those files; do not use Bash heredocs or a standalone `PY` terminator.

Use `$search_command` for unresolved clues, `$read_command` for member evidence and `$neighbors_command` for relation history. For each image, open and inspect the original `image_path` rather than inferring content from metadata. For managed chat attachments, use the receipt hints and installed provenance lookup to match the project ID and managed attachment against the capture receipt or retained framing; preserve every verified chat-part identity in the image locator, and leave an unavailable origin unresolved. Perform the task's reading, chunking, summaries and ordinary repairs within its source/member paths and shared graph targets. Keep unique facts, mandatory material, exact source versions, locators, privacy and unread gaps.

During ordinary reading, look for relationships that could answer a future retrieval question. Read the exact endpoint originals and necessary evidence together and judge direction, applicability and reuse yourself when the material suffices. Use `has_basis` to find original evidence. Draft an independent relationship only when that evidence establishes its meaning and you can name its retrieval use. Return relationships limited to the current reading with the coverage. For each unresolved relationship, hand off the hypothesis, available IDs, versions and locators, and the missing evidence or write scope.

Check the draft direction against the originals before submitting. `in` is the starting vertex and `out` is the destination. For `derived_from`, set `in` to the output and `out` to the actual input that produced it.

For grouped tasks, confirm any `shared_reading` hints against the supplied originals and their context. Preserve independent facts, material outside the named shared ranges, and conflicting evidence. In the coverage and error receipts, identify the affected paths or ranges, evidence, what was completed, and the change needed in a later task when the group or its scope is incomplete.

For facts imported from another source, include and actually read the relevant accepted member records or originals in the fixed reading package. Put the supporting accepted members or in-scope same-batch original chunks in each affected `member.evidence`, so compilation pins their exact prepared or same-batch versions; IDs or paths mentioned only in text are not dependency pins. Read-only preparation does not expand `paths`; missing necessary evidence or write scope requires a bounded unresolved handoff. Original chunks without imported facts may still use `evidence:[]`.

Omit `id` on new nodes and edges so freeze can assign one. For an update, use the existing ID from fixed `prepare`. Shadow graph IDs from offline retrieval experiments stay in those experiments.

Use a string for an existing record ID in `parent`, each `evidence` array entry, and edge `in` or `out`. For a new member use a draft position such as `{"member": 0}`. For a new node endpoint use `{"node": 0}`.

A full-file summary spans line 1 through the current EOF, including framing; a partial summary must state its `coverage_gaps`. For a text read with an explicit `--source-version`, supply the saved `--start-line` and `--end-line`.

For the same source revision, omit an entire dispositions/refinement/unavailable field to retain it; an explicit list replaces that whole field and [] clears it. Before carrying old entries into an extended list, compare their pinned versions and applicability with prepare; changed evidence needs renewed judgment. Unavailable gaps require the exact prepared revision and are never rebound.

Every `sources[].dispositions[]` entry needs `kind: "no_knowledge"` or `kind: "duplicate"`. A duplicate names its existing representations. Put new or updated members in the top-level `members` array.

When you have read the available range, submit source-only `deferred_refinement` only if a fresh file/section summary covers the fact or substance the gap lacks, binding the exact current member, knowledge revision and gap text. Spanning its lines or describing its absence is not enough: approval with no execution result does not cover a missing-result gap. Current `paths` authorizes necessary member corrections even when `write_targets` is empty; no second member authorization is needed. Reuse prior analysis without inheriting its old scope conclusions. For a qualifying source-only review, do not rewrite the member or erase its gap; an adequate summary or coverage receipt alone does not persist that decision. If the member needs correction, read and pin the necessary evidence, correct it now within `paths`, then prepare and review the accepted new knowledge version in a later wave. A specifically checked capture-local absence stays distinct from any externally known result; assess `unavailable_gaps` rather than rename the missing fact fine refinement. Keep unread or otherwise unqualified gaps unresolved and never invent unavailable content.

For a specifically checked unavailable original or historical unknown, use a source-only `unavailable_gaps` entry with the exact current fresh member, `knowledge_revision`, gap text and a brief reason stating the boundary of the source and references actually checked. This does not assert global nonexistence, claim the missing content was read or resolve the gap. Reuse current accepted summaries and fixed prior coverage when their versions still match; read the particular original ranges and direct references needed for this decision, without a full audit of unchanged parent history or unrelated artifacts. If a known direct reference supplies the missing fact, use it for a scoped correction or handoff. Judge each gap individually; do not infer unavailability by pattern or bulk-classify. Keep the reason within the source's privacy scope without copying other restricted content; a public source cannot record a private member's gap. A private-to-public source needs explicit review or clearing of the previous unavailable list. Changed source or member versions reopen the decision; submit a member change first and record its new version only after acceptance in a later wave.

Write one or more scoped proposal JSON drafts plus separate coverage and errors JSON files in this work directory. In the same script, use the basePack Python and the unchanged `reading_path` for the draft and any coverage from that reading.

```python
from basepack.memory.query import normalize_scope
from basepack.memory.stages import _read_reference, fixed_reference

draft["prepare"] = fixed_reference(reading_path)
revisions = {normalize_scope(source["path"]): source["revision"]
             for source in _read_reference(draft["prepare"])["sources"] if not source.get("deleted")}
```

When creating a coverage row for a range you actually read from this file, use its project-relative `approved_path` if you include `source_revision`. Keep older conclusions on their recorded revisions and leave unread ranges unresolved.

```python
coverage_row = {"path": approved_path, "source_revision": revisions[normalize_scope(approved_path)]}
```

Omit `context` from wave drafts. The wave receipt links each fixed draft to your task and worker identity. For each assigned range, record represented, no-knowledge/duplicate, deferred refinement, or unresolved with reason. Record each actual failure in errors as a brief original error and its resolved or unresolved status; do not dump source stdout or replace failures with `[]` after fixing them. After submission keep every referenced file's bytes fixed; a repair uses a new file path and hash. Preserve full fixed references, do not publish, and return to the wave worker loop to submit them. A source-only registration is not semantic coverage. Do not start a separate maintenance run or a new team.
