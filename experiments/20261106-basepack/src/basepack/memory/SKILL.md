---
name: basepack-memory
description: Use an enabled basePack project memory to retrieve evidence, follow semantic relations, or maintain intelligent chunks and summaries after source changes.
---

# Project memory

Read the project's `.basepack/instructions.md` for its explicit config and Python. Invoke that Python with `-m basepack --config <absolute-config> memory ...`; each new process can run brief directly. The client authenticates with `memory.username` and automatically reads the UTF-8 `memory.password_file` (default: the resolved memory directory's `password.txt`; BOM accepted, other text preserved). No password environment bridge is needed. Use `config show` for the resolved file path, and leave secret contents to the client. Missing files, access errors and authentication failures remain errors: restore the correct credential instead of generating a replacement for an existing database. `guide`, `rank` and `stop` process their own inputs without config or credentials; `guide` prints this file's installed location. The authenticated local SurrealDB server must already be running; keep its data in this project.

Before first `memory init`, choose this project's physical directory, endpoint and unique project_id. Another project may use the same exe but needs its own directory/port/UUID; for example A uses 18080 and B uses 18081. Ordinary `basepack init` creates configuration and entry instructions, without starting or creating a database. After a hidden launcher call has ended, verify `/ready` in a separate call, then use the target config for `init`/`brief` to enforce project identity. Keep the actual launcher, cwd, logs and Python locatable in the project's ignored memory directory. First deployment prepares one strong random password file for a new database; the launcher reads that same file and username and binds only to loopback. Reuse existing credentials. Editing the file does not rotate the database's stored account.

Run Python with `-X utf8` and write JSON with UTF-8. Save `.ps1` scripts as UTF-8 with BOM for Windows PowerShell 5.1 to decode Chinese source/path text; program-written JSON and originals use ordinary UTF-8. Each dependent native command must succeed before the next: use `subprocess.run(..., check=True)` or check PowerShell `$LASTEXITCODE` immediately and throw on nonzero. An apply failure ends that chain before embed/search/read; preserve its original error.

At task start or continuation, run `brief --task <goal>` and keep its mandatory content directly. Stale mandatory information remains an obligation to recheck, not a current fact. Brief reads published knowledge and does not scan originals. The map channel also delivers prerequisites sharing no literal task terms. Open the original when a fact matters.

The business-task owner manages the following lifecycle; dispatched maintenance agents follow their rendered role prompts. When the host provides cancellable subagent handles and task start/completion events, independently run `maintain --control <unique-path>` alongside the business task; business work does not wait. Use the default whole-project discovery rather than passing the current task's files as `--scope`. Follow the handoff below only when `needs_semantic` is true. The maintenance coordinator owns continuing work until business completion, exhausted candidates or an actual blockage; one returned reader or published batch is not completion. At business completion run `memory stop --control <path>`, then cancel the coordinator and all its descendants using host handles. Stop arbitrates with publication without waiting for encoding or an already admitted commit. If stop fails, preserve the error and still cancel the agents; publication may already have been admitted. Published batches and collected originals remain, and unaccepted work continues across tasks. Task relevance affects priority, including for historical pending work. If the host lacks these lifecycle capabilities, report automatic maintenance as unavailable and use an explicit maintenance task.

## Retrieve in one delegation

When a task names a few known files, read those files together directly after brief. Use memory when locations, relevant prerequisites or cross-material evidence need discovery. Select the shortest useful evidence set; parent summaries add background or missing conditions rather than repeating already selected chunks.

For memory discovery, delegate the question, project scope and content budget once to a subscription worker with clean history (`fork_turns="none"` where supported). First resolve the project's retrieval tier with `python -m basepack --config <absolute-config> config ai --purpose retrieval`, using the Python from the project instructions. The default is `tier1`; choose another tier explicitly with `config ai --tier <tier>` when difficulty warrants it. Pass the returned `model` and `reasoning_effort` as explicit host parameters. Report an unavailable mapping or host capability with its original error; any tier change or model substitution must be explicit.

That worker owns all needed search rounds, evidence reads, scoring and ranking, then returns usable content and sources:

1. Run `search --text <terms>` and inspect `matches` and `vector_coverage`, using the project's `memory.search_mode` across file/section summaries, original chunks and images. New projects default to `vector`; `hybrid` combines text and compatible vectors. An explicit `--mode vector|hybrid` overrides the project setting. For identifiers, filenames or an intact phrase, use `--mode hybrid --literal`: case-insensitive substrings in path/title/text rank before semantic-only supplements, and direct matches carry `lexical_rank`. Read the results to check the intended meaning. `vector --literal` fails; choose hybrid explicitly. Keep missing configuration, model and compatible-index errors visible.
2. Use `read <member-id>` for a directly selected member, and `neighbors <id>` to expand current parents, children and semantic edges; `--include-stale` is explicit historical inspection. For each semantic claim, follow its `basis`: read every cited `member` with that item's `--source-version`, and its `--start-line`/`--end-line` for text or `--locator` JSON when present for images. For example, `read <basis.member> --source-version <basis.source_version> --start-line <basis.start_line> --end-line <basis.end_line>`. Verify conditions in the returned `original`; the accompanying `member` is the current record. A stable member ID may have been updated, so its current summary, source version or line range cannot substitute for the relation's saved evidence. For images, actually open `original.image_path` and distinguish descriptions from image evidence. A missing snapshot fails. Structural links differ from semantic claims. Read content before scoring.
3. Write a JSON array of actual candidates with `id`, `kind`, `path`, `revision`, `source_version`, `start_line`, `end_line`, `title`, `text`, numeric `score` and a short reason. For original evidence, copy the locators, revision and text from the verified `original`; identify summaries as summaries. Use a common 0–100 relevance scale; a lexical/vector score is not an agent score.
4. Run `rank --input <scored.json> --budget <text-characters>`. Return the selected content, source locators and unresolved gaps. Budget omissions retain reading pointers; whole evidence is not silently truncated. The working agent may read more freely.

Record the selected tier and actual model when available; do not invent usage or price. Keep intermediates under this project's `.basepack/memory/`, uniquely named per batch so concurrent chats do not overwrite each other's work.

The ID contract supports string and integer keys. An ID without a table prefix is a raw string key. A full `member:`/`node:` ID is canonical database syntax; reuse returned IDs unchanged. Raw `123` and canonical `member:123` are different string/integer keys; the canonical string is ``member:`123` ``. Use a full canonical ID for a key containing a colon. A missing read target reports the requested ID and fails.

## Maintain sources

For a Codex desktop host, obtain the current host project's ID and the complete `list_projects` result. Save a UTF-8 JSON object under this project's ignored memory directory with `project_id`, `other_project_roots` (the other local projects on this host) and `registry_complete: true`, and pass `--codex-registry <path>` to `maintain`. Refresh it from the host for each maintenance start. If the host cannot provide these facts, do not invent them; maintain reports the binding gap and file maintenance remains available. The configured `[memory.codex]` binding is an alternative when current. The CLI lists active and archived threads, checks explicit IDs or root/worktree membership against other registered roots, and captures available message bodies; unresolved ownership and unavailable parts are gaps. A readable local image is retained as an independent source. A discovered or captured chat is not yet semantically accepted, and vector coverage only describes accepted representations.

For managed chat images, the maintenance receipt's optional `codex` object supplies `project_id` (the host-assigned project), `receipt` (this run's full capture receipt, when available), `capture_dir` (retained framed chat sources) and `attachment_dir` (managed images). Look up `managed_attachment` in `capture.threads[].locations[]` of the capture receipt; that path is relative to the memory directory, the parent of `capture_dir`. For a retained attachment absent from this run's receipt, walk `capture_dir/*.txt` as UTF-8 records using each header's `byte_length` to locate the next header. In either input, use a record only when its `project_id` matches the handed-off `codex.project_id` and its resolved `managed_attachment` matches the assigned image. An unavailable project ID leaves an origin gap; foreign or unknown records cannot establish ownership. Copy each verified matching record's project/chat-part identity and origin fields into the image member's `locator`, retaining multiple owned origins when they share one image. Keep unavailable origins unresolved rather than reconstructing identity from filenames. Reader hints carry the same pointers and project ID; the identity records remain in their capture receipts and framed originals.

Default discovery inventories Git-tracked and nonignored untracked files within the project, plus explicit `memory.source_scope` includes, excluding generated state, environments and caches. A non-Git project uses its declared `source_scope`. All registered sources, historical pending/unaccepted work and owned Codex captures remain eligible. `--scope <files-or-directories>` overrides new-file discovery, not that global history. Use the reported discovery boundaries and gaps; an inventory is not proof of semantic coverage. Avoid recursively scanning `.` through caches, databases and unsupported binaries.

1. Allocate the unique control path before starting asynchronous `maintain --control <unique-path>`, adding the Codex registry when available, so business completion can stop preflight before its receipt returns. The command completes proven mechanical changes and returns `receipt`, `control`, `discovery`, `needs_semantic` and, when needed, `worker` dispatch metadata. An explicit invocation may omit control and receive an automatically allocated path. Detailed evidence stays in the receipt. `changes` provides explicit discovery and `sources` provides the registered metadata inventory; Git status does not establish freshness.
2. When `needs_semantic` is true, use `worker.model` and `worker.reasoning_effort` as explicit host parameters before spawning a coordinator with clean history. Send exactly one English bootstrap followed by `worker.render_command`:

   ```text
   Run the following command and follow the `prompt` field in its JSON output:
   <worker.render_command>
   ```

   The subagent executes the command itself. `memory prompt --receipt <receipt> --control <control>` renders the shipped coordinator prompt; `--role reader --paths <files...>` renders the reader prompt. Role and model tier are separate: coordinator defaults to tier2 and reader to tier1; `--tier <tier>` resolves another project mapping without changing the role. Returned JSON includes `prompt`, `role`, `tier`, `model`, `reasoning_effort` and `render_command`. Rendering reads configuration, templates and the receipt only; it does not access credentials, the database or models, or write state. Detailed coordinator/reader work belongs to those templates.
3. Keep the coordinator responsible for the next source-grouped batch, readers and evidence verification, using the same control on every apply. Use the receipt's capture cutoff; current-chat additions are next-run work. Report actual failures and coverage gaps. Historical small batches need no separate manual deep-maintenance request. For an exceptional task, adjust organization/discovery scope or send a temporary English prompt directly, briefly stating the reason and coverage.

### Direct batch interface

For an explicit batch, run `prepare --paths <affected-files-and-related-material> --output <reading.json>`, including evidence and both relation endpoints. Read the new/old numbered originals and relevant `neighborhood.members`; use `read` or extend prepare to verify additional originals. Reading units are location hints. Choose semantic chunk boundaries, file/section summaries, nodes and edges in the same reading, with conditions and evidence. Preserve original wording inside chunks.

A zero-line text source needs no text member: registering its prepared source revision is sufficient when it has no active knowledge. When an existing source becomes empty, retire its old text members and resolve dependent knowledge through retirements or corrected evidence in the same batch. Text member ranges remain 1-based and inclusive; an empty source has no valid range.

Write the batch and run `apply --batch <batch.json>`, adding the task's `--control <path>` during automatic maintenance. Reuse stable IDs for unchanged members. The program checks source and knowledge versions, prepares required candidate vectors, then publishes records, relations and matching vectors in one transaction. A changed source requires preparing and reading that batch again; preserve the actual error. Search/read the published result and verify its evidence before calling the batch accepted. Report uncovered ranges and remaining candidates.

Batch fields:

- `expected`: copy this object unchanged from prepare. Apply checks the versions of targets written, retired or corrected, existing evidence members actually used, and relation endpoints. Unused expected entries do not block unrelated writes. Missing versions permit only records created in this batch, protected by an absence check; existing dependencies require versions too. Writes and invalidations advance knowledge versions. On a stale draft conflict, prepare and read the affected material again.
- `sources`: `{path, revision}` from prepare, never the null revision of a fast changes check; image sources add `kind:'image'`. An accepted missing source adds `deleted:true` and its previous revision.
- `members`: `{id, kind, path, parent, start_line, end_line, title, text, evidence, mandatory, coverage_gaps}`. Text kinds are `file`, `section`, `chunk`; line ranges are 1-based and inclusive. Summary evidence names the covered chunks. For chunks, omit text and let the program take exact original bytes/line endings; explicitly supplied text is strictly checked. Images use `kind:'image'`, actual visual description/OCR as text, and `locator` for page/region/origin as available; no invented line range. Mark only explicitly required startup information mandatory.
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
$work = '<absolute-memory.data_dir>/example-<unique-name>'
function memory {
    & $python -X utf8 -m basepack --config $config memory @args
    if ($LASTEXITCODE -ne 0) { throw "memory command failed ($LASTEXITCODE)" }
}
New-Item -ItemType Directory -Path $work | Out-Null
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
memory apply --batch $batch
memory search --text 'A-17' --mode hybrid --literal
memory search --text 'memory-example.md' --mode hybrid --literal
memory read 'member:`example-chunk`'
memory neighbors 'member:`example-section`'
```

Apply encodes the candidate members before publishing them with matching vectors. The function above stops on any failed dependency, including model errors. A text member missing start_line/end_line reports its batch position, member ID and field; correct the input and rerun. Failed batches leave no partial database writes.

An explicit deep pass may use `sources` to sample old materials and seek missed relations. Read sampled material with its old neighborhood, including `--include-stale` for history, and record a discovered relation or an honest negative result. It extends ordinary background maintenance rather than enabling historical eligibility. Do not claim every source pair was examined.

Back up with SurrealDB's native export and restore into a separate project directory. Include this project's configuration, original documents/images and the assets directory under configured `memory.data_dir`. Database exports preserve explicitly stored knowledge/history; rebuilding vectors uses the accepted representations and retained image snapshots.

The shared embedding service encodes text as title plus accepted text, and images as original image bytes. Descriptions do not substitute for image vectors. `embedding_identity` and input revisions gate compatibility; equal dimensions do not. A missing compatible index is an explicit error: index accepted members with `embed`. Model errors stop publication or retrieval with their original details. Over-limit representations return to the same reader to adjust semantic boundaries/summaries while retaining their coverage and exceptions. A timeout only ends waiting and does not cancel shared inference.
