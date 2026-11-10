---
name: basepack-memory
description: Use an enabled basePack project memory to retrieve evidence, follow semantic relations, or maintain intelligent chunks and summaries after source changes.
---

# Project memory

Read the project's `.basepack/instructions.md` for its explicit config and Python. In each new process, execute its credential-loading block before memory actions; it reads the current config and sets the configured environment variable from the local secret file. Invoke that Python with `-m basepack --config <absolute-config> memory ...`. The local SurrealDB server must already be running; keep its data in this project. `guide` prints this file's installed location; action help describes arguments.

Before first `memory init`, choose this project's physical directory, endpoint and unique project_id. Another project may use the same exe but needs its own directory/port/UUID; for example A uses 18080 and B uses 18081. Ordinary `basepack init` creates configuration and entry instructions, without starting or creating a database. After a hidden launcher call has ended, verify `/ready` in a separate call, then use the target config for `init`/`brief` to enforce project identity. Keep the actual launcher, cwd, logs, credential source and Python locatable in the project's ignored memory directory.

Run Python with `-X utf8` and write JSON with UTF-8. Save `.ps1` scripts as UTF-8 with BOM for Windows PowerShell 5.1 to decode Chinese source/path text; program-written JSON and originals use ordinary UTF-8. Each dependent native command must succeed before the next: use `subprocess.run(..., check=True)` or check PowerShell `$LASTEXITCODE` immediately and throw on nonzero. An apply failure ends that chain before embed/search/read; preserve its original error.

At task start or continuation, run `brief --task <goal>`. Keep current `mandatory` content directly; stale mandatory information remains an obligation to recheck, not a current fact. Brief fast-checks registered originals and configured `memory.source_scope`. If changes/pending affect the task, maintain a necessary small batch within the task, optionally combined with the retrieval delegation; explicitly hand off remaining work. The map channel also delivers prerequisites sharing no literal task terms. Open the original when a fact matters.

## Retrieve in one delegation

When a task names a few known files, read those files together directly after brief. Use memory when locations, relevant prerequisites or cross-material evidence need discovery. Select the shortest useful evidence set; parent summaries add background or missing conditions rather than repeating already selected chunks.

For memory discovery, delegate the question, project scope and content budget once to a subscription worker with clean history (`fork_turns="none"` where supported). First resolve the project's retrieval tier with `python -m basepack --config <absolute-config> config ai --purpose retrieval`, using the Python from the project instructions. The default is `tier1`; choose another tier explicitly with `config ai --tier <tier>` when difficulty warrants it. Pass the returned `model` and `reasoning_effort` as explicit host parameters. Report an unavailable mapping or host capability with its original error; any tier change or model substitution must be explicit.

That worker owns all needed search rounds, evidence reads, scoring and ranking, then returns usable content and sources:

1. Run `search --text <terms>` using the project's `memory.search_mode` across file/section summaries, original chunks and images. New projects default to `text`; `hybrid` combines text and compatible vectors, and `vector` queries only compatible vectors. An explicit `--mode text|hybrid|vector` overrides the project setting. Existing 0.6.2 projects must add this setting explicitly before default search; keep missing configuration and facility errors visible. Chinese segmentation is not substring matching; use `--literal --mode text` for case-insensitive substrings in stored titles/text, including identifiers or missed proper names.
2. Use `neighbors <id>` to expand current parents, children and semantic edges; `--include-stale` is explicit historical inspection. Follow evidence member IDs and use `read <member-id>` to verify original ranges and conditions. For images, actually open `original.image_path`; distinguish the saved description from image evidence and report original_missing. A missing business original still permits reading its retained snapshot; a changed original or missing snapshot fails. Structural links differ from semantic claims. Read content before scoring.
3. Write a JSON array of actual candidates with `id`, `kind`, `path`, `revision`, `start_line`, `end_line`, `title`, `text`, numeric `score` and a short reason. Use a common 0–100 relevance scale; a lexical/vector score is not an agent score.
4. Run `rank --input <scored.json> --budget <text-characters>`. Return the selected content, source locators and unresolved gaps. Budget omissions retain reading pointers; whole evidence is not silently truncated. The working agent may read more freely.

Record the selected tier and actual model when available; do not invent usage or price. Keep intermediates under this project's `.basepack/memory/`, uniquely named per batch so concurrent chats do not overwrite each other's work.

The ID contract supports string and integer keys. An ID without a table prefix is a raw string key. A full `member:`/`node:` ID is canonical database syntax; reuse returned IDs unchanged. Raw `123` and canonical `member:123` are different string/integer keys; the canonical string is ``member:`123` ``. Use a full canonical ID for a key containing a colon. A missing read target reports the requested ID and fails.

## Read and maintain together

1. Run `changes --scope <explicit-files-or-directories>` after edits or when checking freshness. Fast checks use metadata; `--deep` hashes originals when needed. Configure `memory.source_scope` to discover new files in declared directories; without it, startup checks registered paths only. Brief caps detail lists and reports total counts; `sources` gives the full metadata inventory for explicit maintenance.
2. Run `prepare --paths <affected-files-and-related-material> --output <reading.json>`, including the material used as evidence and at both relation endpoints. Read the new/old numbered originals and `neighborhood.members` with relevant neighbors; use `read` or extend prepare paths to verify additional originals. Reading units are location hints. Decide the final semantic chunk boundaries, file/section summaries, knowledge nodes and semantic edges during this same reading, including conditions and evidence. Preserve original wording inside chunks.
3. Write one batch and run `apply --batch <batch.json>`. Reuse stable IDs for unchanged members. The program checks source versions, writes native records/relations transactionally, preserves snapshots/corrections and invalidates affected dependencies. A source changed during the work requires another reading of that batch; preserve actual errors.
4. For a project using vectors, run `embed` to encode accepted current members through the existing shared service, or `embed --ids <member-ids>` for an explicit batch. It reuses compatible unchanged vectors and reports pending members. A text-only project can defer embedding with `memory.search_mode = 'text'`. Search/read changed knowledge using the configured mode and ensure old conclusions are no longer current. Report uncovered ranges and remaining stale knowledge.

Batch fields:

- `expected`: copy this object unchanged from prepare. Apply checks the versions of targets written, retired or corrected, existing evidence members actually used, and relation endpoints. Unused expected entries do not block unrelated writes. Missing versions permit only records created in this batch, protected by an absence check; existing dependencies require versions too. Writes and invalidations advance knowledge versions. On a stale draft conflict, prepare and read the affected material again.
- `sources`: `{path, revision}` from prepare, never the null revision of a fast changes check; image sources add `kind:'image'`. An accepted missing source adds `deleted:true` and its previous revision.
- `members`: `{id, kind, path, parent, start_line, end_line, title, text, evidence, mandatory, coverage_gaps}`. Text kinds are `file`, `section`, `chunk`; line ranges are 1-based and inclusive. Summary evidence names the covered chunks. For chunks, omit text and let the program take exact original bytes/line endings; explicitly supplied text is strictly checked. Images use `kind:'image'`, actual visual description/OCR as text, and `locator` for page/region/origin as available; no invented line range. Mark only explicitly required startup information mandatory.
- `nodes`: optional `{id, kind, text, evidence}` for entities, decisions and conditions.
- `edges`: optional `{id, in, out, kind, text, conditions, evidence}`. Endpoints name `member:<id>` or `node:<id>`; evidence names member IDs read together. Edit an existing edge by its ID; adding one preserves other edges.
- `delete_members`, `delete_nodes`, `delete_edges`: explicit IDs retired by this batch. `corrections`: `{id, target, reason}`; the program captures the previous record.
- `context`: actual available `chat`, `turn`, `root_chat`; leave unavailable fields absent.

### Minimal text batch

Use an initialized disposable project with credentials already loaded. This standalone example creates exactly four UTF-8 lines. Choose a fresh work directory and source filename; the file/section/chunk ranges are inclusive, all parents and evidence exist in the same batch, and chunk text comes from the original. The example summaries describe this fixed source; actual material requires the same reading and judgment described above.

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
[IO.File]::WriteAllText($source, "# 试用说明`n## 约定`n试用问题留在开发记录。`n项目数据库按项目隔离。`n", [Text.UTF8Encoding]::new($false))
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
         "text": "试用问题留在开发记录；项目数据库按项目隔离。", "evidence": ["member:`example-chunk`"]},
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
memory search --text '项目数据库' --mode text --literal
memory read 'member:`example-chunk`'
memory neighbors 'member:`example-section`'
```

With the configured shared embedding service, continue with `memory embed --ids example-file example-section example-chunk`, then `memory search --text '项目数据库' --mode hybrid` and ``memory read 'member:`example-chunk`'``. Set `memory.search_mode = 'hybrid'` when this should be the project's persistent default. The function above stops on any failed dependency. A text member missing start_line/end_line reports its batch position, member ID and field; correct the input and rerun. Failed batches leave no partial database writes.

For broad maintenance, use a coordinator and at most four readers per coordinator. Resolve each role through the project tier mapping: use the routine default (`tier3` by default), adjusting the tier to difficulty. Merge cross-worker candidates and read both ends together before accepting a relation. Batch review is optional. Deep maintenance may revisit old or randomly selected material to seek missed relations; do not claim every pair was examined.

For a manual deep pass, use `sources`, sample distinct materials within the declared scope, then actually read those materials together with their old neighborhood, including `--include-stale` when inspecting history. Record a discovered relation or an honest negative result. Extend the evidence of an existing relation when new material supports it; preserve other valid edges and explicit conditions. After a source disappears, reread remaining evidence before deciding whether a claim survives.

Back up with SurrealDB's native export and restore into a separate project directory. Include this project's configuration, original documents/images and the assets directory under configured `memory.data_dir`. Database exports preserve explicitly stored knowledge/history; rebuilding vectors from retained representations still requires the business originals to exist at their accepted revisions.

The shared embedding service encodes text as title plus accepted text, and images as original image bytes. Descriptions do not substitute for image vectors. `embedding_identity` and input revisions gate compatibility; equal dimensions do not. A missing compatible index is an explicit error: index accepted members or choose text mode. Preserve service errors; do not retry or truncate silently. Over-limit representations return to the same reader to adjust semantic boundaries/summaries while retaining their coverage and exceptions. A timeout only ends waiting and does not cancel shared inference.
