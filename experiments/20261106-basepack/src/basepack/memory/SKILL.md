---
name: basepack-memory
description: Use an enabled basePack project memory to retrieve evidence, follow semantic relations, or maintain intelligent chunks and summaries after source changes.
---

# Project memory

Read the project's `.basepack/instructions.md` for its explicit config and Python. In each new process, follow its startup block before memory actions. Invoke that Python with `-m basepack --config <absolute-config> memory ...`. The local SurrealDB server must already be running; keep its data in this project. `guide` prints this file's installed location; action help describes arguments.

Before first `memory init`, choose this project's physical directory, endpoint and unique project_id. Another project may use the same exe but needs its own directory/port/UUID; for example A uses 18080 and B uses 18081. Ordinary `basepack init` creates configuration and entry instructions, without starting or creating a database. After a hidden launcher call has ended, verify `/ready` in a separate call, then use the target config for `init`/`brief` to enforce project identity. Keep the actual launcher, cwd, logs and Python locatable in the project's ignored memory directory.

Run Python with `-X utf8` and write JSON with UTF-8. Save `.ps1` scripts as UTF-8 with BOM for Windows PowerShell 5.1 to decode Chinese source/path text; program-written JSON and originals use ordinary UTF-8. Each dependent native command must succeed before the next: use `subprocess.run(..., check=True)` or check PowerShell `$LASTEXITCODE` immediately and throw on nonzero. An apply failure ends that chain before embed/search/read; preserve its original error.

At task start or continuation, run `brief --task <goal>` and keep its mandatory content directly. Stale mandatory information remains an obligation to recheck, not a current fact. Brief reads published knowledge and does not scan originals. The map channel also delivers prerequisites sharing no literal task terms. Open the original when a fact matters.

When the host provides a cancellable subagent handle and task start/completion events, independently start `maintain --control <unique-path>` alongside the business task; do not wait for preflight. The command runs deterministic maintenance first and returns a receipt path and semantic-work indication. Only when it reports semantic work, delegate that receipt to one low-priority maintenance worker, passing the same `--control <path>` on each `apply`. At business completion run `memory stop --control <path>` and cancel that worker using the host handle. The stop call arbitrates with publication and does not wait for encoding or an already admitted commit. If it fails, report the error and still cancel the worker; do not claim publication was stopped. Published batches remain, unpublished work is left pending. Historical small batches may continue across tasks; task relevance sets priority, not eligibility. When discovered backlog is substantial, suggest separate manual deep maintenance, which requires the user to initiate it; continue ordinary automatic small batches while the task lasts. If the host cannot provide these lifecycle capabilities, report that automatic maintenance is unavailable and leave maintenance to an explicit task.

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

For a Codex desktop host, obtain the current host project's ID and the complete `list_projects` result. Save a UTF-8 JSON object under this project's ignored memory directory with `project_id`, `other_project_roots` (the other local projects on this host) and `registry_complete: true`, and pass `--codex-registry <path>` to `maintain`. Refresh it from the host for each maintenance start. If the host cannot provide these facts, do not invent them; maintain reports the binding gap and file maintenance remains available. The configured `[memory.codex]` binding is an alternative when current. The CLI lists active and archived threads, checks explicit IDs or root/worktree membership against other registered roots, and captures available message bodies; unresolved ownership and unavailable parts are gaps. A readable local image is retained as an independent source; use its chat part identity and locator from the capture receipt when accepting its image member. A discovered or captured chat is not yet semantically accepted, and vector coverage only describes accepted representations.

1. Run `maintain --control <unique-path>` for the configured source scope, or supply `--scope <explicit-files-or-directories>`. It compares current originals with accepted snapshots, handles proven mechanical changes, and writes detailed material under the project memory directory. Read its receipt for remaining semantic work, including older pending records. `changes` remains available for explicit source discovery; Git status does not establish memory freshness. `sources` gives the metadata inventory.
2. Run `prepare --paths <affected-files-and-related-material> --output <reading.json>`, including the material used as evidence and at both relation endpoints. Read the new/old numbered originals and `neighborhood.members` with relevant neighbors; use `read` or extend prepare paths to verify additional originals. Reading units are location hints. Decide the final semantic chunk boundaries, file/section summaries, knowledge nodes and semantic edges during this same reading, including conditions and evidence. Preserve original wording inside chunks.
3. Write one batch and run `apply --batch <batch.json>`. Reuse stable IDs for unchanged members. The program checks source and knowledge versions, prepares required candidate vectors, then publishes records, relations and matching vectors in one transaction; snapshots and corrections are retained. A source changed during the work requires another reading of that batch; preserve actual errors.
4. Search/read the published knowledge using the configured mode and check its evidence. Report uncovered ranges and discovered backlog. Before upgrading a project configured with `search_mode = 'text'`, use its existing client to run `embed` as needed, then query with `search --mode vector` and confirm published vector coverage has `total = compatible` and `pending = 0`. Compatible unchanged vectors are reused. Then change the configuration to `vector` or `hybrid` and upgrade the client. If the new client is already installed, `embed` and explicit `search --mode vector` still support preparing and checking coverage before switching the configuration.

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

For broad maintenance, use a tier2 coordinator and at most four tier1 readers per coordinator. Resolve each role through the project tier mapping. Merge cross-worker candidates and read both ends together before accepting a relation. Batch review is optional. Deep maintenance may revisit old or randomly selected material to seek missed relations; do not claim every pair was examined.

For a manual deep pass, use `sources`, sample distinct materials within the declared scope, then actually read those materials together with their old neighborhood, including `--include-stale` when inspecting history. Record a discovered relation or an honest negative result. Extend the evidence of an existing relation when new material supports it; preserve other valid edges and explicit conditions. After a source disappears, reread remaining evidence before deciding whether a claim survives.

Back up with SurrealDB's native export and restore into a separate project directory. Include this project's configuration, original documents/images and the assets directory under configured `memory.data_dir`. Database exports preserve explicitly stored knowledge/history; rebuilding vectors uses the accepted representations and retained image snapshots.

The shared embedding service encodes text as title plus accepted text, and images as original image bytes. Descriptions do not substitute for image vectors. `embedding_identity` and input revisions gate compatibility; equal dimensions do not. A missing compatible index is an explicit error: index accepted members with `embed`. Model errors stop publication or retrieval with their original details. Over-limit representations return to the same reader to adjust semantic boundaries/summaries while retaining their coverage and exceptions. A timeout only ends waiting and does not cancel shared inference.
