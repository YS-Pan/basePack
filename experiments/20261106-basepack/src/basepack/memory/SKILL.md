---
name: basepack-memory
description: Use enabled basePack memory for task-start briefs, long-task maintenance, evidence retrieval, use feedback, or an explicitly requested memory audit.
---

# Project memory

## Start and stop

Follow the project's generated `.basepack/instructions.md#startup` for its Python, explicit config and task-start steps. Initialize only the parameters and UTF-8 settings needed by each new shell; retain the same task's brief across later reads, edits, feedback and cleanup. Refresh the brief when the task goal or context materially changes. Invoke commands with `-X utf8 -m basepack --config <absolute-config> memory ...`.

The client reads `memory.username` and the UTF-8 `memory.password_file` (default: the resolved memory directory's `password.txt`; BOM accepted). Use `config show` for its resolved path; restore the correct credential after a missing-file, permission or authentication error. `guide` and `rank` need no config or credentials. Ownership actions need project config but no database, credentials or preceding brief. Knowledge actions require the project's authenticated local SurrealDB server.

Before first `memory init`, choose this project's physical directory, endpoint and unique project_id. Another project may use the same exe but needs its own directory/port/UUID; for example A uses 18080 and B uses 18081. Ordinary `basepack init` creates configuration and entry instructions, without starting or creating a database. After a hidden launcher call has ended, verify `/ready` in a separate call, then use the target config for `init`/`brief` to enforce project identity. Keep the actual launcher, cwd, logs and Python locatable in the project's ignored memory directory. First deployment prepares one strong random password file for a new database; the launcher reads that same file and username and binds only to loopback. Reuse existing credentials. Editing the file does not rotate the database's stored account.

Run Python with `-X utf8` and write JSON with UTF-8. Save `.ps1` scripts as UTF-8 with BOM for Windows PowerShell 5.1 to decode Chinese source/path text; program-written JSON and originals use ordinary UTF-8. Each dependent native command must succeed before the next: use `subprocess.run(..., check=True)` or check PowerShell `$LASTEXITCODE` immediately and throw on nonzero. An apply failure ends that chain before embed/search/read; preserve its original error.

Brief directly reads published mandatory information, existing file/section summaries and known gaps. It performs no embedding or task search and does not scan originals. Keep mandatory content; stale mandatory information is an obligation to recheck rather than a current fact. Use retrieval below for task-specific discovery, including project context and earlier requirements. Open the evidence when a fact matters.

When the business task intuitively takes at most ten minutes, skip the entire automatic `maintain`, including preflight and ownership. For an obviously longer task, start once alongside business work when the host supports cancellable subagent handles and task start/completion events. Report brief and maintenance-start failures independently; a failed brief must not silently skip an otherwise due start. Reassess when scope materially expands; a short task may then start its first maintenance run without waiting for a timer. Dispatched agents follow their briefs and rendered prompts rather than recursively starting maintenance. An explicit request to maintain memory uses manual maintenance regardless of duration.

Allocate a fresh control under the configured memory directory's `maintenance/` and run `maintain --mode automatic --holder <host-thread-identity> --control <path>`. If the host already exposes available subagent capacity, add `--available-subagents <A>` after other occupied slots, including retrieval workers, but before the script's business reserve. The command atomically acquires project ownership before preflight. If `acquired=false`, report the existing owner and continue business. Use whole-project discovery. With ownership and `needs_semantic=true`, follow the handoff below. The coordinator continues until business completion, exhausted fixed candidates or an actual blockage. One reader or batch is not completion. Hosts lacking this lifecycle report automatic maintenance unavailable and use an explicit maintenance task.

At business completion run `memory stop --control <own-path>`, cancel the coordinator and descendants, then inspect `memory owner` and run `memory release --control <same-path>` after publication has ended. Run this cleanup independently of brief or database availability. Stop arbitrates admission; an admitted commit may still be running. Release refuses active or uncertain publication. Keep the owner and original error when outcome is unresolved, and report this remainder without indefinitely delaying the business answer. Only the holder releases its ownership; control paths are capabilities and must never be reused. For an abandoned owner, independently verify the old host task has ended and publication is resolved, then explicitly use `memory recover-owner --run-id <id> --owner-ended --publication-resolved`. File age is not recovery evidence. Published work and originals remain for later tasks. An explicitly requested maintenance task reports what the authorized scope actually resolved and what remains blocked; another owner or a few priority batches do not satisfy it.

## Retrieve in one delegation

When a task names a few known files, read them together directly. Before judging project status, remaining work, pending decisions or historical requirements, use one complete retrieval delegation to establish prior decisions before forming options. Read named chats directly and follow related publication work. Use retrieval also to discover locations, prerequisites and cross-material evidence. Parent summaries supply missing context rather than repeat selected chunks.

Run the unified entry with the project's Python/config prefix:

```text
memory retrieve --question 'How have the requirements changed?'
memory retrieve --question 'Which documented constraints apply?' --scope 'devDoc/'
```

The default scope is `''` (the whole project) and the default text-character budget is 6000 (`--budget` overrides it). Scope is strictly a project-relative path prefix, supporting Chinese and spaces; put business restrictions in `question`. A worker may broaden a path filter within the same question, stating which filter changed. `retrieve` creates `tmp/basepack-retrieval/<uuid>/request.json` with a stable `delivery_id`, and returns `request`, `work`, `delivery_receipt` and dispatch details. Resume that request with `retrieve --request <path>`; omit `--question` then. A call without a question or request returns the required input and starts no work.

The CLI prepares dispatch; it cannot spawn the host's agents. The host must actually create the returned `task_name` with the returned `model` and `reasoning_effort` (configured retrieval tier, default tier1), clean history, and receive its final result. Pass only this bootstrap and the returned command:

```text
Run the following command and follow the `prompt` field in its JSON output:
<render_command>
```

Use `--available-subagents <A>` when the host exposes shared capacity and distinct `--slot` indices for independent concurrent questions. Reuse an owned handle for further rounds of the same question. An explicit `--tier <tier>` changes the configured mapping. Preserve name, capacity and mapping errors. `prepared`/`started=false` is not a dispatched worker. When `executor='main'` or the host cannot spawn, the main agent executes the same rendered flow and reports the actual executor. Retrieval uses no maintenance owner/control and shares host capacity with maintenance.

One executor owns all search rounds, current-state evidence, reading, integration, scoring and ranking. Run `memory freshness` and inspect its new, possibly changed, covered and unknown classes, receipt and endpoints; for relevant candidates and named chats run `memory freshness --thread <id>` to read and compare actual paginated text. Use the host chat reader for named or linked chats outside this project, including publication follow-ups. Timestamps and endpoints are clues, not proof of body equality; unknown candidates, non-text parts and semantic acceptance remain explicit. This probe does not acquire an owner, capture sources, embed or publish knowledge. Return the per-chat cutoff, known uncaptured/changed material, actual supplementary reads and unknowns with the answer:

1. Run `search --text <terms>` and inspect `matches` and `vector_coverage`. Scope uses the same path-prefix meaning in search. Search defaults to the project's `memory.search_mode`; `--mode vector|hybrid` overrides it. For identifiers, filenames or intact phrases use `--mode hybrid --literal`; direct substring matches carry `lexical_rank` before semantic supplements. Keep configuration, model and compatible-index errors visible.
2. Preserve every candidate's observed `id` and `knowledge_revision`. Use `knowledge <id> --knowledge-revision <version>` for that accepted representation, `history <id>` for available versions, and `neighbors <id> --knowledge-revision <version>` for relationships; `--include-stale` explicitly includes stale relationships. Check applicability using accepted evolution relations, task conditions and necessary original evidence, distinguishing user requirements, working assumptions, implementation facts and experiment observations. Follow each saved `basis` through `read <basis.member> --knowledge-revision <observed-version> --source-version <basis.source_version>` plus its saved line range or image `--locator`; open `original.image_path` for images. A knowledge version identifies the representation; `source_version`/`revision` and locators identify its original evidence. Only provably retained versions are available; history does not promise complete reconstruction at every past time.
3. Read before scoring. Use `access_weight` as an auxiliary history-of-use clue; relevance, applicability and evidence value determine the common 0–100 comprehensive score. Low weight does not exclude important evidence or override accepted replacement/retraction. If needed, `access-hints --input <items.json>` takes `[{"id":"<observed-id>","knowledge_revision":"<observed-version>"}]`.
4. Actually save a UTF-8 `scored.json` array using the host's file tool or local Python. Each item retains observed `id`, `knowledge_revision`, native `kind`, `title`, `text`, any returned `private`, numeric `score` and a short `reason`, plus the observed `private` marker when present. Members use `record_type:'member'` (or omit it), `path`, `revision`, `source_version`, `start_line` and `end_line`; images use null line fields and the actual `locator`. Nodes use `record_type:'node'`; semantic relationships use `record_type:'semantic'`. Those graph representations may be pathless: retain their actual `basis`/`endpoint_versions` without inventing source paths or line ranges. Copy original evidence text and locators from verified `original` and identify summaries as summaries.
5. Run `rank --input <scored.json> --budget <text-characters>`. Rank uses the comprehensive score directly for sorting, deduplication and budget selection; it adds no second access weighting and records no delivery. Return usable selected content, the same observed knowledge versions, source locators and unresolved gaps. Keep reading pointers for budget omissions rather than truncating conditions.

The host confirms which final content it actually received, then saves the returned delivery receipt path as `{"delivery_id":"<request delivery_id>","items":[{"id":"<actually delivered id>","knowledge_revision":"<actually observed version>"}]}` (optional `context` may contain JSON) and runs `memory delivery --input <receipt.json>`. Record only the delivered representations, with no propagation to parents, evidence or neighbors. Reusing the same `delivery_id` is idempotent; an empty item list advances no event. Never look up a current version to fill an older delivered identity. Search/read/rank and internal errors are not delivery.

Report completed stages from evidence. If saving or ranking fails, preserve the original error and already read evidence and name the unfinished stage; a prepared request, unsaved array or rank file is not a complete retrieval or observed host delivery. A final partial delivery with exact observed identities can still be recorded after host receipt. Report problems through [use feedback](#use-feedback).

Record the selected tier and actual model when available; do not invent usage or price. Keep reading, ranking and batch intermediates under the project root's `tmp/<task-or-run>/`, uniquely named for concurrent work. Retain selected long-term evidence under root `artifacts/runs/<run>/`. Configuration, credentials, database, managed originals/assets, active controls, receipts and capture identity records stay in their configured persistent locations. Cleanup must preserve current and historical source references and unresolved publication state.

Members use program-generated UUIDs; reuse their returned IDs unchanged. Other record tables may use string or integer keys; reuse their full returned IDs, especially when a key contains a colon. A missing read target reports the requested ID and fails.

## Private sources and publication

The program computes `private: true|false` for new sources, source snapshots, members, nodes and semantic relationships. Source flags use the normalized project-relative root `private/` path. Members include their own source version and pinned basis; nodes use pinned basis; relationships include basis and pinned endpoint versions. Any private dependency makes the whole record private, including mixed public/private knowledge. Use the referenced versions rather than their current flags. Stale, retired and retained historical records preserve their flags. An optional private-path reference in public text alone does not establish use of private content. Authors declare actual evidence; the program derives this metadata rather than accepting an author-selected privacy classification.

Preserve returned flags through search, brief, read, scoring, rank and handoff with their observed knowledge versions. `read.original.private` describes the selected source snapshot and can differ from a member with private cross-source evidence. An absent legacy flag is unknown, not verified public. Treat private content as confidential when writing public files or outputs; derive only conclusions the project's publication rules permit. Keep manually maintained confidential originals and derivatives inside the project's private boundary. Managed memory snapshots/assets and reading/batch/ranking packages remain in their existing ignored persistent or temporary locations and are private local runtime material.

Flags provide neither access control nor automatic redaction. Native exports and complete backups retain public and private content. A future public sharing copy must filter actual snapshots, assets, historical records, `change.previous`, and chat/feedback/delivery context as well as current knowledge; no public-export helper is provided. Scoped legacy metadata upgrades use confirmed source mappings and pinned evidence, preserving identities, knowledge/input versions and unchanged vectors; keep unconfirmed coverage explicit.

## Maintain sources

For a Codex desktop host, obtain the current host project's ID and the complete `list_projects` result. Save a UTF-8 JSON object in the task's temporary work directory with `project_id`, `other_project_roots` (other registered local project roots) and `registry_complete: true`, and pass `--codex-registry <path>` to `maintain`. Refresh it for each start. If unavailable, keep the binding gap explicit; file maintenance remains available. Current configured `[memory.codex]` is an alternative. The CLI lists active/archived threads, checks explicit IDs or root/worktree membership against other roots, and captures available bodies. A readable local image is an independent source. Discovery/capture is not semantic acceptance; vector coverage describes accepted representations.

For managed chat images, the maintenance receipt's optional `codex` object supplies `project_id` (the host-assigned project), `receipt` (this run's full capture receipt, when available), `capture_dir` (retained framed chat sources) and `attachment_dir` (managed images). Look up `managed_attachment` in `capture.threads[].locations[]` of the capture receipt; that path is relative to the memory directory, the parent of `capture_dir`. For a retained attachment absent from this run's receipt, walk `capture_dir/*.txt` as UTF-8 records using each header's `byte_length` to locate the next header. In either input, use a record only when its `project_id` matches the handed-off `codex.project_id` and its resolved `managed_attachment` matches the assigned image. An unavailable project ID leaves an origin gap; foreign or unknown records cannot establish ownership. Copy each verified matching record's project/chat-part identity and origin fields into the image member's `locator`, retaining multiple owned origins when they share one image. Keep unavailable origins unresolved rather than reconstructing identity from filenames. Reader hints carry the same pointers and project ID; the identity records remain in their capture receipts and framed originals.

Default discovery inventories Git-tracked and nonignored untracked files within the project, plus explicit `memory.source_scope` includes; a non-Git project uses its declared `source_scope`. It also includes tracked and nonignored files from the root `private/` independent Git repository, respecting its own ignores without per-file source_scope configuration. They share the outer project's UUID, database and lifecycle. An absent private directory completes normally. Exclude `.git/`, generated state, environments and caches throughout. All registered sources, historical pending/unaccepted work and owned Codex captures remain eligible. `--scope <files-or-directories>` overrides new-file discovery without appending the private range; it does not restrict global history or change the existing missing-source contract. Use the reported discovery boundaries and gaps; an inventory is not proof of semantic coverage. Avoid recursively scanning `.` through caches, databases and unsupported binaries.

1. Allocate the fresh persistent control before asynchronous `maintain --mode automatic --holder <host-thread> --control <path>`, adding the Codex registry and available capacity when obtainable. Explicit maintenance uses `--mode manual` (the command default). Ownership covers mechanical preflight and semantic work. An occupied project returns `acquired=false` with the existing `owner`; each thread can still brief, report feedback and do business. An acquired run completes proven mechanical changes and returns `receipt`, `control`, `discovery`, `needs_semantic`, fixed `layout` and, when needed and capacity permits, `worker`. Preserve actual preflight errors and inspect owner/publication status before recovery. Detailed evidence stays in the receipt. `changes` inventories differences and `sources` gives registered metadata; Git status does not establish freshness.
2. When `needs_semantic` is true and `worker` is present, set `worker.task_name`, `worker.model` and `worker.reasoning_effort` as explicit host parameters before spawning the coordinator with clean history. Send exactly one English bootstrap followed by `worker.render_command`:

   ```text
   Run the following command and follow the `prompt` field in its JSON output:
   <worker.render_command>
   ```

   The subagent executes the command itself. `memory prompt --receipt <receipt> --control <control> --team 0` renders the publisher prompt; `--team <t> --role reader --reader <r> --paths <files...>` renders a reader's prompt. Other coordinator teams require bounded `--paths` too: replace the source placeholder in their returned render commands with the assigned real files before dispatch. Names, parent-child placement, quotas, model and effort come from the script; role and tier stay separate (coordinator defaults to tier2, reader to tier1). Rendering reads configuration, templates and the fixed receipt layout only; it does not access credentials, the database or models, or write state. Configuration changes affect a new run, not this layout. Detailed role work belongs to the rendered templates.
3. Follow the saved `layout`: automatic maintenance uses team 0 only; manual maintenance uses full teams when capacity permits and a single coordinator at low capacity. With zero readers, that coordinator personally prepares, reads originals, generates all knowledge and publishes. Team 0's coordinator is the sole publisher and feedback resolver; other teams return drafts, hashes, coverage and remainders through its subtree. All teams share one owner/control/receipt. Enable fewer whole teams when material is insufficient; leave unused quota free. Reuse known owned handles across batches and, after a resolved prior run, across new controls; names alone never authorize reuse.
4. If the host rejects capacity, stop new dispatch and retain the original error and unstarted slots. With newly known capacity, `pending-dispatch --receipt <path> --available-subagents <A> --started-task-names <names...>` reduces only the unstarted list; retain existing names, permissions and layout. Without capacity, pending work remains pending. Continue the next source-grouped batch using the same control on every apply. The receipt fixes candidates and chat cutoff; each prepare reads its then-current files, not an atomic project-wide start snapshot. New material outside the receipt is later work. Authors read necessary originals while generating knowledge; coordinator-created cross-reader relations require their originals read together. After successful program publication, ordinary creation, maintenance and feedback repair need no independent semantic review, routine read/search checks or post-batch audit. Report failures, unresolved feedback, coverage and deferred refinement honestly. Historical candidates require no separate deep-maintenance request.

### Direct batch interface

For an explicit batch, run `prepare --paths <affected-files-and-related-material> --output <reading.json>`, including evidence and both relation endpoints. Read the new/old numbered originals and relevant `neighborhood.members`; use `read` or extend prepare to verify additional originals. Reading units are location hints. Choose semantic chunk boundaries, file/section summaries, nodes and edges in the same reading, with conditions and evidence. Preserve original wording inside chunks.

A zero-line text source needs no text member: registering its prepared source revision is sufficient when it has no active knowledge. When an existing source becomes empty, retire its old text members and resolve dependent knowledge through retirements or corrected evidence in the same batch. Text member ranges remain 1-based and inclusive; an empty source has no valid range.

Acquire project ownership as above and write one draft per reader. Run `memory freeze --drafts <draft1.json> <draft2.json> --output <new-batch.json>`, then `apply --batch <new-batch.json> --control <same-path>`. The output must not already exist. Freeze allocates member UUIDs and records their mapping in the batch; keep that exact file for retry or outcome verification. Apply recognizes an already committed identical batch and returns its receipt. A changed batch requires a new freeze. Existing members are updated using their UUID and expected revision returned by prepare. The program checks sources, knowledge and parent dependencies, prepares candidate vectors and publishes knowledge with matching vectors atomically. A changed source requires preparing and reading that batch again; preserve the actual error. Successful publication completes the batch. Report uncovered ranges, dispositions, deferred refinement and remaining candidates; failed or uncertain publication is unresolved.

Draft fields (freeze resolves scoped member references into the persisted batch):

- For a new member omit `id`. For an update use its UUID returned by prepare; never invent one. `{"member": 0}` refers to the first member in the same draft. To refer to another draft, use `{"draft": 1, "member": 0}`: both indexes are zero-based and `draft` follows the exact `--drafts` order. Each reader retains a separate draft scope; a coordinator co-reads cross-reader evidence before authoring relations. Identical titles or positions across scopes do not identify the same object. Duplicate updates and conflicting expected revisions fail rather than merge.
- References in member `parent`/`evidence` and node/edge `evidence`, edge `in`/`out` accept these scoped objects or existing IDs from prepare. Source dispositions and historical endpoint pins refer only to already published IDs and versions.

Other fields:

- `expected`: copy this object unchanged from prepare. Apply checks the versions of targets written, retired or corrected, existing evidence members actually used, and relation endpoints. Unused expected entries do not block unrelated writes. Missing versions permit only records created in this batch, protected by an absence check; existing dependencies require versions too. Writes and invalidations advance knowledge versions. On a stale draft conflict, prepare and read the affected material again.
- `sources`: `{path, revision}` from prepare, never the null revision of a fast changes check; image sources add `kind:'image'`. An accepted missing source adds `deleted:true` and its previous revision.
- A source may add `dispositions: [{kind:'no_knowledge'|'duplicate', start_line, end_line, reason, representations:[{id, knowledge_revision}]}]` for actually read ranges. Images use `whole_image:true` instead of line ranges. Duplicate representations require their current versions from prepare. Valid same-version dispositions avoid repeated initial work; partial reading covers only its ranges. Source changes invalidate old dispositions; relevant representation changes reopen duplicate work.
- `deferred_refinement: [{start_line, end_line, reason, gaps:[{member, gap, knowledge_revision}]}]` records read coverage whose finer representation is deferred, separate from unread gaps and dispositions. Images use `whole_image:true`. Each gap names the exact current fresh member version and exact `coverage_gaps` text; changing that member in the same batch requires publishing it before deferring its gap. Deferred text counts as handled only where current fresh file/section summaries cover it; a chunk plus defer cannot stand in for coarse delivery. Existing selected chunks still support summaries. Preserve unique facts and fine knowledge, and explicitly retain mandatory flags when rewriting members. Same-version omitted dispositions/refinement remain; a new source revision does not inherit them.
- `members`: `{kind, path, parent, start_line, end_line, title, text, evidence, mandatory, coverage_gaps}` plus `id` only for an existing member; optional `conditions` and `claim_type` state applicability and claim identity. The program pins `parent_version` to the accepted parent. Text kinds are `file`, `section`, `chunk`; line ranges are 1-based and inclusive. A full file summary spans line 1 through the source's final line, including framing/header lines; its evidence chunks may cover the meaningful body. A partial file summary declares actual `coverage_gaps`. Summary evidence names the covered chunks. For chunks, omit text and let the program take exact original bytes/line endings; explicitly supplied text is strictly checked. Images use `kind:'image'`, actual visual description/OCR as text, and `locator` for page/region/origin as available; no invented line range. Mark only explicitly required startup information mandatory.
- `nodes`: optional `{id, kind, text, evidence, conditions, claim_type}` for entities, decisions and conditions.
- `edges`: optional `{id, in, out, kind, text, conditions, evidence}`. Endpoints name `member:<id>` or `node:<id>`; evidence names member IDs read together. Optional `endpoint_versions:{in:{id,knowledge_revision},out:{id,knowledge_revision}}` links retained historical endpoints; when omitted the program pins the actual versions accepted in this batch. Edit an existing edge by its ID; adding one preserves other edges.
- `delete_members`, `delete_nodes`, `delete_edges`: explicit IDs retired by this batch. `corrections`: `{id, target, reason}`; the program captures the previous record.
- `context`: actual available `chat`, `turn`, `root_chat`; leave unavailable fields absent.

### Minimal batch

Use an initialized disposable project, the configured shared embedding service available, and `memory.search_mode` set to `vector` or `hybrid`. This standalone example creates exactly four UTF-8 lines. Choose a fresh work directory and source filename; the file/section/chunk ranges are inclusive, all parents and evidence exist in the same batch, and chunk text comes from the original. The example summaries describe this fixed source; actual material requires the same reading and judgment described above.

```powershell
$ErrorActionPreference = 'Stop'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
$python = '<instructions absolute-python.exe>'
$config = '<absolute-project-config>'
$projectRoot = '<absolute-project>'
$work = Join-Path $projectRoot 'tmp/example-<unique-name>'
$control = '<absolute-memory.data_dir>/maintenance/example-<fresh-unique-name>.control'
function memory {
    & $python -X utf8 -m basepack --config $config memory @args
    if ($LASTEXITCODE -ne 0) { throw "memory command failed ($LASTEXITCODE)" }
}
New-Item -ItemType Directory -Path $work | Out-Null
memory maintain --mode manual --holder '<this-host-thread>' --control $control
# Proceed only when acquired=true; an occupied project belongs to the returned owner.
$source = Join-Path $projectRoot 'memory-example.md'
New-Item -ItemType File -Path $source | Out-Null
[IO.File]::WriteAllText($source, "# 试用说明`n## 约定`n试用问题 A-17 留在开发记录。`n项目数据库按项目隔离。`n", [Text.UTF8Encoding]::new($false))
$reading = Join-Path $work 'reading.json'
$draft = Join-Path $work 'draft.json'
$batch = Join-Path $work 'batch.json'
memory prepare --paths 'memory-example.md' --output $reading
@'
import json, sys
from pathlib import Path
reading = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
source = reading["sources"][0]
print(source["numbered_text"])
path = source["path"]
batch = {
    "expected": reading["expected"],
    "sources": [{"path": path, "revision": source["revision"]}],
    "members": [
        {"kind": "file", "path": path, "parent": None,
         "start_line": 1, "end_line": 4, "title": "试用说明",
         "text": "试用问题 A-17 留在开发记录；项目数据库按项目隔离。", "evidence": [{"member": 2}]},
        {"kind": "section", "path": path, "parent": {"member": 0},
         "start_line": 2, "end_line": 4, "title": "约定",
         "text": "保留试用记录，并使用独立项目数据库。", "evidence": [{"member": 2}]},
        {"kind": "chunk", "path": path, "parent": {"member": 1},
         "start_line": 3, "end_line": 4, "title": "试用与隔离约定", "evidence": []},
    ],
}
Path(sys.argv[2]).write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
'@ | & $python -X utf8 - $reading $draft
if ($LASTEXITCODE -ne 0) { throw "Batch creation failed ($LASTEXITCODE)" }
memory freeze --drafts $draft --output $batch
memory apply --batch $batch --control $control
memory search --text 'A-17' --mode hybrid --literal
memory search --text 'memory-example.md' --mode hybrid --literal
$frozen = Get-Content -Raw -Encoding UTF8 $batch | ConvertFrom-Json
memory read $frozen.members[2].id
memory neighbors $frozen.members[1].id
memory stop --control $control
memory release --control $control
```

Apply encodes the candidate members before publishing them with matching vectors. The function above stops on any failed dependency, including model errors. A text member missing start_line/end_line reports its batch position, member ID and field; correct the input and rerun. Failed batches leave no partial database writes.

## Use feedback

Retrieval workers and calling agents use the same lightweight report action: `feedback-report --kind knowledge|retrieval --issue <concern>`. For a target, add `--target <returned-id> --observed-revision <observed-knowledge_revision>`; preserve the version seen in search/brief rather than replacing it with a later read. This is the observed knowledge version; put the software version in the issue description. For a miss without an ID, provide `--query <query>` or `--source <expected-source-or-locator>`. Optional `--reporter <host-identity>` identifies the observer. Report the concern and available evidence; a separate audit or complete repair proposal is unnecessary. Continue business using reliable evidence and expose relevant gaps.

`feedback-list` returns unresolved reports (`--all` includes results). Reports persist in the project database and native exports, never become discoverable business sources, and trigger the next owner maintenance even with unchanged originals and no other candidates. Reporting does not require ownership. Only the maintenance owner judges and repairs current knowledge using normal apply/corrections. Resolve with `feedback-resolve <id> --control <same-path> --outcome fixed|invalid|duplicate|obsolete --result <reason>`; for a target include its current `--expected-revision`. Preserve stale-report conflicts and unresolved outcomes. A retrieval/ranking problem is not automatically a knowledge error.

## Manual audit

Only an explicit user intent to audit the memory system starts an audit. Interpret intent rather than matching an exact phrase; discussing audit, asking ordinary maintenance, or reporting a problem does not trigger one. Fix the authorized scope and cutoff, read the requested evidence and record findings through the same feedback interface. Read-only audit/reporting may coexist with maintenance; writing repairs acquires the single project owner. Resolve findings according to the user's request and report unexamined scope. Ordinary creation and repair remain complete after author judgment and successful program submission.

Back up with SurrealDB's native export and restore into a separate project directory. Include configuration, public/private original documents/images, the independent private Git and needed files it ignores, managed chat/attachment originals and identity receipts, and assets under configured `memory.data_dir`; a database export alone does not contain all these files. Exports preserve available knowledge versions/evolution, private flags, source dispositions/refinement, feedback, access state and delivery deduplication IDs; an older backup cannot restore later state or unrecorded history. Retain needed controls and receipts while publication or recovery depends on them. Rebuilding vectors uses accepted representations and retained image snapshots; delivery accounting does not rebuild them. Choose backup location and retention for an explicit recovery need, and keep complete recovery material within its private sharing boundary.

The shared embedding service encodes text as title plus accepted text, and images as original image bytes. Descriptions do not substitute for image vectors. `embedding_identity` and input revisions gate compatibility; equal dimensions do not. A missing compatible index is an explicit error: index accepted members with `embed`. Keep summaries short. HTTP 422 reports 0-based input indices and token counts; candidate errors add the member key, path and range. Preserve the unpublished batch and original error, then return over-limit text to the same reader: split original chunks at semantic boundaries or shorten summaries and prepare again, retaining coverage and exceptions. Resume from the reported path/range without truncating originals, raising the service limit or automatically resubmitting. Other model errors retain their original details. A timeout only ends waiting and does not cancel shared inference.
