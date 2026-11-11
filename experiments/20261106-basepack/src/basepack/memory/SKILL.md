---
name: basepack-memory
description: Use enabled basePack memory for task-start maintenance, evidence retrieval, use feedback, or an explicitly requested memory audit.
---

# Project memory

## Start and stop

Read the project's `.basepack/instructions.md` for its explicit config and Python. Invoke that Python with `-m basepack --config <absolute-config> memory ...`; each new process can run brief directly. The client authenticates with `memory.username` and automatically reads the UTF-8 `memory.password_file` (default: the resolved memory directory's `password.txt`; BOM accepted, other text preserved). No password environment bridge is needed. Use `config show` for the resolved file path, and leave secret contents to the client. Missing files, access errors and authentication failures remain errors: restore the correct credential instead of generating a replacement for an existing database. `guide` and `rank` process their inputs without config or credentials; `guide` prints this file's installed location. Ownership actions need project config but no database credentials. The authenticated local SurrealDB server must already be running for knowledge actions; keep its data in this project.

Before first `memory init`, choose this project's physical directory, endpoint and unique project_id. Another project may use the same exe but needs its own directory/port/UUID; for example A uses 18080 and B uses 18081. Ordinary `basepack init` creates configuration and entry instructions, without starting or creating a database. After a hidden launcher call has ended, verify `/ready` in a separate call, then use the target config for `init`/`brief` to enforce project identity. Keep the actual launcher, cwd, logs and Python locatable in the project's ignored memory directory. First deployment prepares one strong random password file for a new database; the launcher reads that same file and username and binds only to loopback. Reuse existing credentials. Editing the file does not rotate the database's stored account.

Run Python with `-X utf8` and write JSON with UTF-8. Save `.ps1` scripts as UTF-8 with BOM for Windows PowerShell 5.1 to decode Chinese source/path text; program-written JSON and originals use ordinary UTF-8. Each dependent native command must succeed before the next: use `subprocess.run(..., check=True)` or check PowerShell `$LASTEXITCODE` immediately and throw on nonzero. An apply failure ends that chain before embed/search/read; preserve its original error.

At task start or continuation, run `brief --task <goal>` and keep its mandatory content directly. Stale mandatory information remains an obligation to recheck, not a current fact. Brief reads published knowledge and does not scan originals. The map channel also delivers prerequisites sharing no literal task terms. Open the original when a fact matters.

The business-task owner manages maintenance; dispatched agents follow their rendered prompts. With cancellable subagent handles and task start/completion events, allocate a fresh control under the configured memory directory's `maintenance/` and run `maintain --holder <host-thread-identity> --control <path>` alongside business work. The command atomically acquires project ownership before preflight. If `acquired=false`, report the existing owner and continue business; do not dispatch another maintenance team. Use whole-project discovery. With ownership and `needs_semantic=true`, follow the handoff below. The coordinator continues until business completion, exhausted fixed candidates or an actual blockage. One reader or batch is not completion. Hosts lacking this lifecycle report automatic maintenance unavailable and use an explicit maintenance task.

At business completion run `memory stop --control <own-path>`, cancel the coordinator and descendants, then inspect `memory owner` and run `memory release --control <same-path>` after publication has ended. Stop arbitrates admission; an admitted commit may still be running. Release refuses active or uncertain publication. Keep the owner and original error when outcome is unresolved, and report this remainder without indefinitely delaying the business answer. Only the holder releases its ownership; control paths are capabilities and must never be reused. For an abandoned owner, independently verify the old host task has ended and publication is resolved, then explicitly use `memory recover-owner --run-id <id> --owner-ended --publication-resolved`. File age is not recovery evidence. Published work and originals remain for later tasks. An explicitly requested maintenance task reports what the authorized scope actually resolved and what remains blocked; another owner or a few priority batches do not satisfy it.

## Retrieve in one delegation

When a task names a few known files, read those files together directly after brief. Use memory when locations, relevant prerequisites or cross-material evidence need discovery. Select the shortest useful evidence set; parent summaries add background or missing conditions rather than repeating already selected chunks.

For memory discovery, delegate the question, project scope and content budget once to a subscription worker with clean history (`fork_turns="none"` where supported). First resolve the project's retrieval tier with `python -m basepack --config <absolute-config> config ai --purpose retrieval`, using the Python from the project instructions. The default is `tier1`; choose another tier explicitly with `config ai --tier <tier>` when difficulty warrants it. Pass the returned `model` and `reasoning_effort` as explicit host parameters. Report an unavailable mapping or host capability with its original error; any tier change or model substitution must be explicit.

That worker owns all needed search rounds, evidence reads, scoring and ranking, then returns usable content and sources:

1. Run `search --text <terms>` and inspect `matches` and `vector_coverage`, using the project's `memory.search_mode` across file/section summaries, original chunks and images. New projects default to `vector`; `hybrid` combines text and compatible vectors. An explicit `--mode vector|hybrid` overrides the project setting. For identifiers, filenames or an intact phrase, use `--mode hybrid --literal`: case-insensitive substrings in path/title/text rank before semantic-only supplements, and direct matches carry `lexical_rank`. Read the results to check the intended meaning. `vector --literal` fails; choose hybrid explicitly. Keep missing configuration, model and compatible-index errors visible.
2. Use `read <member-id>` and `neighbors <id>` for the evidence needed by the business question; `--include-stale` is explicit historical inspection. When relying on a semantic claim's saved evidence, follow its `basis` using that item's `--source-version` and `--start-line`/`--end-line` or image `--locator`. For example, `read <basis.member> --source-version <basis.source_version> --start-line <basis.start_line> --end-line <basis.end_line>`. The returned `original` is the saved evidence; the accompanying member is current and cannot substitute for that version. Open `original.image_path` when using image evidence. Read selected content before scoring. Choose the evidence needed for the answer rather than auditing every hit and evidence chain. Report problems encountered through [use feedback](#use-feedback).
3. Write a JSON array of actual candidates with `id`, `kind`, `path`, `revision`, `source_version`, `start_line`, `end_line`, `title`, `text`, numeric `score` and a short reason. For original evidence, copy the locators, revision and text from the verified `original`; identify summaries as summaries. Use a common 0–100 relevance scale; a lexical/vector score is not an agent score.
4. Run `rank --input <scored.json> --budget <text-characters>`. Return the selected content, source locators and unresolved gaps. Budget omissions retain reading pointers; whole evidence is not silently truncated. The working agent may read more freely.

Record the selected tier and actual model when available; do not invent usage or price. Keep reading, ranking and batch intermediates under the project root's `tmp/<task-or-run>/`, uniquely named for concurrent work. Retain selected long-term evidence under root `artifacts/runs/<run>/`. Configuration, credentials, database, managed originals/assets, active controls, receipts and capture identity records stay in their configured persistent locations. Cleanup must preserve current and historical source references and unresolved publication state.

The ID contract supports string and integer keys. An ID without a table prefix is a raw string key. A full `member:`/`node:` ID is canonical database syntax; reuse returned IDs unchanged. Raw `123` and canonical `member:123` are different string/integer keys; the canonical string is ``member:`123` ``. Use a full canonical ID for a key containing a colon. A missing read target reports the requested ID and fails.

## Maintain sources

For a Codex desktop host, obtain the current host project's ID and the complete `list_projects` result. Save a UTF-8 JSON object in the task's temporary work directory with `project_id`, `other_project_roots` (other registered local project roots) and `registry_complete: true`, and pass `--codex-registry <path>` to `maintain`. Refresh it for each start. If unavailable, keep the binding gap explicit; file maintenance remains available. Current configured `[memory.codex]` is an alternative. The CLI lists active/archived threads, checks explicit IDs or root/worktree membership against other roots, and captures available bodies. A readable local image is an independent source. Discovery/capture is not semantic acceptance; vector coverage describes accepted representations.

For managed chat images, the maintenance receipt's optional `codex` object supplies `project_id` (the host-assigned project), `receipt` (this run's full capture receipt, when available), `capture_dir` (retained framed chat sources) and `attachment_dir` (managed images). Look up `managed_attachment` in `capture.threads[].locations[]` of the capture receipt; that path is relative to the memory directory, the parent of `capture_dir`. For a retained attachment absent from this run's receipt, walk `capture_dir/*.txt` as UTF-8 records using each header's `byte_length` to locate the next header. In either input, use a record only when its `project_id` matches the handed-off `codex.project_id` and its resolved `managed_attachment` matches the assigned image. An unavailable project ID leaves an origin gap; foreign or unknown records cannot establish ownership. Copy each verified matching record's project/chat-part identity and origin fields into the image member's `locator`, retaining multiple owned origins when they share one image. Keep unavailable origins unresolved rather than reconstructing identity from filenames. Reader hints carry the same pointers and project ID; the identity records remain in their capture receipts and framed originals.

Default discovery inventories Git-tracked and nonignored untracked files within the project, plus explicit `memory.source_scope` includes, excluding generated state, environments and caches. A non-Git project uses its declared `source_scope`. All registered sources, historical pending/unaccepted work and owned Codex captures remain eligible. `--scope <files-or-directories>` overrides new-file discovery, not that global history. Use the reported discovery boundaries and gaps; an inventory is not proof of semantic coverage. Avoid recursively scanning `.` through caches, databases and unsupported binaries.

1. Allocate the fresh persistent control before asynchronous `maintain --holder <host-thread> --control <path>`, adding the Codex registry when available. Ownership covers mechanical preflight and semantic work. An occupied project returns `acquired=false` with the existing `owner`; each thread can still brief, report feedback and do business. An acquired run completes proven mechanical changes and returns `receipt`, `control`, `discovery`, `needs_semantic` and, when needed, `worker`. Preserve actual preflight errors and inspect owner/publication status before recovery. Detailed evidence stays in the receipt. `changes` inventories differences and `sources` gives registered metadata; Git status does not establish freshness.
2. When `needs_semantic` is true, use `worker.model` and `worker.reasoning_effort` as explicit host parameters before spawning a coordinator with clean history. Send exactly one English bootstrap followed by `worker.render_command`:

   ```text
   Run the following command and follow the `prompt` field in its JSON output:
   <worker.render_command>
   ```

   The subagent executes the command itself. `memory prompt --receipt <receipt> --control <control>` renders the shipped coordinator prompt; `--role reader --paths <files...>` renders the reader prompt. Role and model tier are separate: coordinator defaults to tier2 and reader to tier1; `--tier <tier>` resolves another project mapping without changing the role. Returned JSON includes `prompt`, `role`, `tier`, `model`, `reasoning_effort` and `render_command`. Rendering reads configuration, templates and the receipt only; it does not access credentials, the database or models, or write state. Detailed coordinator/reader work belongs to those templates.
3. Keep the coordinator responsible for the next source-grouped batch and readers, using the same control on every apply. The receipt fixes candidates and chat cutoff; each prepare reads its then-current files, not an atomic project-wide start snapshot. New material outside the receipt is later work. Authors read necessary originals while generating knowledge; coordinator-created cross-reader relations require their originals read together. After successful program publication, ordinary creation, maintenance and feedback repair need no independent semantic review, routine read/search checks or post-batch audit. Report failures, unresolved feedback, coverage and deferred refinement honestly. Historical candidates require no separate deep-maintenance request.

### Direct batch interface

For an explicit batch, run `prepare --paths <affected-files-and-related-material> --output <reading.json>`, including evidence and both relation endpoints. Read the new/old numbered originals and relevant `neighborhood.members`; use `read` or extend prepare to verify additional originals. Reading units are location hints. Choose semantic chunk boundaries, file/section summaries, nodes and edges in the same reading, with conditions and evidence. Preserve original wording inside chunks.

A zero-line text source needs no text member: registering its prepared source revision is sufficient when it has no active knowledge. When an existing source becomes empty, retire its old text members and resolve dependent knowledge through retirements or corrected evidence in the same batch. Text member ranges remain 1-based and inclusive; an empty source has no valid range.

Acquire project ownership as above, write the batch and run `apply --batch <batch.json> --control <same-path>`. Reuse stable IDs for unchanged members. The program checks sources, knowledge and parent dependencies, prepares candidate vectors and publishes knowledge with matching vectors atomically. A changed source requires preparing and reading that batch again; preserve the actual error. Successful publication completes the batch. Report uncovered ranges, dispositions, deferred refinement and remaining candidates; failed or uncertain publication is unresolved.

Batch fields:

- `expected`: copy this object unchanged from prepare. Apply checks the versions of targets written, retired or corrected, existing evidence members actually used, and relation endpoints. Unused expected entries do not block unrelated writes. Missing versions permit only records created in this batch, protected by an absence check; existing dependencies require versions too. Writes and invalidations advance knowledge versions. On a stale draft conflict, prepare and read the affected material again.
- `sources`: `{path, revision}` from prepare, never the null revision of a fast changes check; image sources add `kind:'image'`. An accepted missing source adds `deleted:true` and its previous revision.
- A source may add `dispositions: [{kind:'no_knowledge'|'duplicate', start_line, end_line, reason, representations:[{id, knowledge_revision}]}]` for actually read ranges. Images use `whole_image:true` instead of line ranges. Duplicate representations require their current versions from prepare. Valid same-version dispositions avoid repeated initial work; partial reading covers only its ranges. Source changes invalidate old dispositions; relevant representation changes reopen duplicate work.
- `deferred_refinement: [{start_line, end_line, reason, gaps:[{member, gap, knowledge_revision}]}]` records read coverage whose finer representation is deferred, separate from unread gaps and dispositions. Images use `whole_image:true`. Each gap names the exact current fresh member version and exact `coverage_gaps` text; changing that member in the same batch requires publishing it before deferring its gap. Deferred text counts as handled only where current fresh file/section summaries cover it; a chunk plus defer cannot stand in for coarse delivery. Existing selected chunks still support summaries. Preserve unique facts and fine knowledge, and explicitly retain mandatory flags when rewriting members. Same-version omitted dispositions/refinement remain; a new source revision does not inherit them.
- `members`: `{id, kind, path, parent, start_line, end_line, title, text, evidence, mandatory, coverage_gaps}`. Text kinds are `file`, `section`, `chunk`; line ranges are 1-based and inclusive. A full file summary spans line 1 through the source's final line, including framing/header lines; its evidence chunks may cover the meaningful body. A partial file summary declares actual `coverage_gaps`. Summary evidence names the covered chunks. For chunks, omit text and let the program take exact original bytes/line endings; explicitly supplied text is strictly checked. Images use `kind:'image'`, actual visual description/OCR as text, and `locator` for page/region/origin as available; no invented line range. Mark only explicitly required startup information mandatory.
- `nodes`: optional `{id, kind, text, evidence}` for entities, decisions and conditions.
- `edges`: optional `{id, in, out, kind, text, conditions, evidence}`. Endpoints name `member:<id>` or `node:<id>`; evidence names member IDs read together. Edit an existing edge by its ID; adding one preserves other edges.
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
memory maintain --holder '<this-host-thread>' --control $control
# Proceed only when acquired=true; an occupied project belongs to the returned owner.
$source = Join-Path $projectRoot 'memory-example.md'
New-Item -ItemType File -Path $source | Out-Null
[IO.File]::WriteAllText($source, "# 试用说明`n## 约定`n试用问题 A-17 留在开发记录。`n项目数据库按项目隔离。`n", [Text.UTF8Encoding]::new($false))
$reading = Join-Path $work 'reading.json'
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
        {"id": "example-file", "kind": "file", "path": path, "parent": None,
         "start_line": 1, "end_line": 4, "title": "试用说明",
         "text": "试用问题 A-17 留在开发记录；项目数据库按项目隔离。", "evidence": ["member:`example-chunk`"]},
        {"id": "example-section", "kind": "section", "path": path, "parent": "member:`example-file`",
         "start_line": 2, "end_line": 4, "title": "约定",
         "text": "保留试用记录，并使用独立项目数据库。", "evidence": ["member:`example-chunk`"]},
        {"id": "example-chunk", "kind": "chunk", "path": path, "parent": "member:`example-section`",
         "start_line": 3, "end_line": 4, "title": "试用与隔离约定", "evidence": []},
    ],
}
Path(sys.argv[2]).write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
'@ | & $python -X utf8 - $reading $batch
if ($LASTEXITCODE -ne 0) { throw "Batch creation failed ($LASTEXITCODE)" }
memory apply --batch $batch --control $control
memory search --text 'A-17' --mode hybrid --literal
memory search --text 'memory-example.md' --mode hybrid --literal
memory read 'member:`example-chunk`'
memory neighbors 'member:`example-section`'
memory stop --control $control
memory release --control $control
```

Apply encodes the candidate members before publishing them with matching vectors. The function above stops on any failed dependency, including model errors. A text member missing start_line/end_line reports its batch position, member ID and field; correct the input and rerun. Failed batches leave no partial database writes.

## Use feedback

Retrieval workers and calling agents use the same lightweight report action: `feedback-report --kind knowledge|retrieval --issue <concern>`. For a target, add `--target <returned-id> --observed-revision <observed-knowledge_revision>`; preserve the version seen in search/brief rather than replacing it with a later read. For a miss without an ID, provide `--query <query>` or `--source <expected-source-or-locator>`. Optional `--reporter <host-identity>` identifies the observer. Report the concern and available evidence; a separate audit or complete repair proposal is unnecessary. Continue business using reliable evidence and expose relevant gaps.

`feedback-list` returns unresolved reports (`--all` includes results). Reports persist in the project database and native exports, never become discoverable business sources, and trigger the next owner maintenance even with unchanged originals and no other candidates. Reporting does not require ownership. Only the maintenance owner judges and repairs current knowledge using normal apply/corrections. Resolve with `feedback-resolve <id> --control <same-path> --outcome fixed|invalid|duplicate|obsolete --result <reason>`; for a target include its current `--expected-revision`. Preserve stale-report conflicts and unresolved outcomes. A retrieval/ranking problem is not automatically a knowledge error.

## Manual audit

Only an explicit user intent to audit the memory system starts an audit. Interpret intent rather than matching an exact phrase; discussing audit, asking ordinary maintenance, or reporting a problem does not trigger one. Fix the authorized scope and cutoff, read the requested evidence and record findings through the same feedback interface. Read-only audit/reporting may coexist with maintenance; writing repairs acquires the single project owner. Resolve findings according to the user's request and report unexamined scope. Ordinary creation and repair remain complete after author judgment and successful program submission.

Back up with SurrealDB's native export and restore into a separate project directory. Include configuration, original documents/images, managed chat/attachment originals and identity receipts, and assets under configured `memory.data_dir`. Native exports preserve knowledge/history, source dispositions/refinement and feedback reports/results; old seven-table exports cannot restore later feedback. Retain needed controls and receipts while publication or recovery depends on them. Rebuilding vectors uses accepted representations and retained image snapshots. Choose backup location and retention for an explicit recovery need.

The shared embedding service encodes text as title plus accepted text, and images as original image bytes. Descriptions do not substitute for image vectors. `embedding_identity` and input revisions gate compatibility; equal dimensions do not. A missing compatible index is an explicit error: index accepted members with `embed`. Model errors stop publication or retrieval with their original details. Over-limit representations return to the same reader to adjust semantic boundaries/summaries while retaining their coverage and exceptions. A timeout only ends waiting and does not cancel shared inference.
