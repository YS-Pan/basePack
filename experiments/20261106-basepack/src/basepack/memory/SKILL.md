---
name: basepack-memory
description: Use an enabled basePack project memory to retrieve evidence, follow semantic relations, or maintain intelligent chunks and summaries after source changes.
---

# Project memory

Read the project's `.basepack/instructions.md` for its explicit config and Python. Invoke that Python with `-m basepack --config <absolute-config> memory ...`. The local SurrealDB server must already be running; keep its data in this project. Credentials come from the configured environment variable. `guide` prints this file's installed location; action help describes arguments.

At task start or continuation, run `brief --task <goal>`. Keep current `mandatory` content directly; stale mandatory information remains an obligation to recheck, not a current fact. Brief fast-checks registered originals and configured `memory.source_scope`. If changes/pending affect the task, maintain a necessary small batch within the task, optionally combined with the retrieval delegation; explicitly hand off remaining work. The map channel also delivers prerequisites sharing no literal task terms. Open the original when a fact matters.

## Retrieve in one delegation

When a task names a few known files, read those files together directly after brief. Use memory when locations, relevant prerequisites or cross-material evidence need discovery. Select the shortest useful evidence set; parent summaries add background or missing conditions rather than repeating already selected chunks.

The working agent may delegate the question, project scope and content budget once to a subscription worker. That worker completes retrieval and scoring, then returns usable content and sources:

1. Run `search --text <terms>` for default hybrid retrieval across file/section summaries, original chunks and images. `--mode text` is the explicit text-only path; `--mode vector` queries only compatible vectors. Chinese segmentation is not substring matching; use `--literal --mode text` for case-insensitive substrings in stored titles/text, including identifiers or missed proper names.
2. Use `neighbors <id>` to expand current parents, children and semantic edges; `--include-stale` is explicit historical inspection. Follow evidence member IDs and use `read <member-id>` to verify original ranges and conditions. For images, actually open `original.image_path`; distinguish the saved description from image evidence and report original_missing. A missing business original still permits reading its retained snapshot; a changed original or missing snapshot fails. Structural links differ from semantic claims. Read content before scoring.
3. Write a JSON array of actual candidates with `id`, `kind`, `path`, `revision`, `start_line`, `end_line`, `title`, `text`, numeric `score` and a short reason. Use a common 0–100 relevance scale; a lexical/vector score is not an agent score.
4. Run `rank --input <scored.json> --budget <text-characters>`. Return the selected content, source locators and unresolved gaps. Budget omissions retain reading pointers; whole evidence is not silently truncated. The working agent may read more freely.

Use a cheaper available worker for routine retrieval. Record its actual model when available; do not invent usage or price. Keep intermediates under this project's `.basepack/memory/`, uniquely named per batch so concurrent chats do not overwrite each other's work.

## Read and maintain together

1. Run `changes --scope <explicit-files-or-directories>` after edits or when checking freshness. Fast checks use metadata; `--deep` hashes originals when needed. Configure `memory.source_scope` to discover new files in declared directories; without it, startup checks registered paths only. Brief caps detail lists and reports total counts; `sources` gives the full metadata inventory for explicit maintenance.
2. Run `prepare --paths <affected-files-and-related-material> --output <reading.json>`, including the material used as evidence and at both relation endpoints. Read the new/old numbered originals and `neighborhood.members` with relevant neighbors; use `read` or extend prepare paths to verify additional originals. Reading units are location hints. Decide the final semantic chunk boundaries, file/section summaries, knowledge nodes and semantic edges during this same reading, including conditions and evidence. Preserve original wording inside chunks.
3. Write one batch and run `apply --batch <batch.json>`. Reuse stable IDs for unchanged members. The program checks source versions, writes native records/relations transactionally, preserves snapshots/corrections and invalidates affected dependencies. A source changed during the work requires another reading of that batch; preserve actual errors.
4. Run `embed` to encode accepted current members through the existing shared service, or `embed --ids <member-ids>` for an explicit batch. It reuses compatible unchanged vectors and reports pending members. Then search/read changed knowledge and ensure old conclusions are no longer current. A text-only project may defer embedding and use `--mode text`. Report uncovered ranges and remaining stale knowledge.

Batch fields:

- `expected`: copy this object unchanged from prepare. Apply checks the versions of targets written, retired or corrected, existing evidence members actually used, and relation endpoints. Unused expected entries do not block unrelated writes. Missing versions permit only records created in this batch, protected by an absence check; existing dependencies require versions too. Writes and invalidations advance knowledge versions. On a stale draft conflict, prepare and read the affected material again.
- `sources`: `{path, revision}` from prepare, never the null revision of a fast changes check; image sources add `kind:'image'`. An accepted missing source adds `deleted:true` and its previous revision.
- `members`: `{id, kind, path, parent, start_line, end_line, title, text, evidence, mandatory, coverage_gaps}`. Text kinds are `file`, `section`, `chunk`; line ranges are 1-based and inclusive. Summary evidence names the covered chunks. For chunks, omit text and let the program take exact original bytes/line endings; explicitly supplied text is strictly checked. Images use `kind:'image'`, actual visual description/OCR as text, and `locator` for page/region/origin as available; no invented line range. Mark only explicitly required startup information mandatory.
- `nodes`: optional `{id, kind, text, evidence}` for entities, decisions and conditions.
- `edges`: optional `{id, in, out, kind, text, conditions, evidence}`. Endpoints name `member:<id>` or `node:<id>`; evidence names member IDs read together. Edit an existing edge by its ID; adding one preserves other edges.
- `delete_members`, `delete_nodes`, `delete_edges`: explicit IDs retired by this batch. `corrections`: `{id, target, reason}`; the program captures the previous record.
- `context`: actual available `chat`, `turn`, `root_chat`; leave unavailable fields absent.

For broad maintenance, use a coordinator and at most four cheaper readers per coordinator. Merge cross-worker candidates and read both ends together before accepting a relation. Batch review is optional. Deep maintenance may revisit old or randomly selected material to seek missed relations; do not claim every pair was examined.

For a manual deep pass, use `sources`, sample distinct materials within the declared scope, then actually read those materials together with their old neighborhood, including `--include-stale` when inspecting history. Record a discovered relation or an honest negative result. Extend the evidence of an existing relation when new material supports it; preserve other valid edges and explicit conditions. After a source disappears, reread remaining evidence before deciding whether a claim survives.

Back up with SurrealDB's native export and restore into a separate project directory. Include this project's configuration, original documents/images and the assets directory under configured `memory.data_dir`. Database exports preserve explicitly stored knowledge/history; rebuilding vectors from retained representations still requires the business originals to exist at their accepted revisions.

The shared embedding service encodes text as title plus accepted text, and images as original image bytes. Descriptions do not substitute for image vectors. `embedding_identity` and input revisions gate compatibility; equal dimensions do not. A missing compatible index is an explicit error: index accepted members or choose text mode. Preserve service errors; do not retry or truncate silently. Over-limit representations return to the same reader to adjust semantic boundaries/summaries while retaining their coverage and exceptions. A timeout only ends waiting and does not cancel shared inference.
