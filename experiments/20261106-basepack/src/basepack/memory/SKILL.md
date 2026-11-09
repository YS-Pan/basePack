---
name: basepack-memory
description: Use an enabled basePack project memory to retrieve evidence, follow semantic relations, or maintain intelligent chunks and summaries after source changes.
---

# Project memory

Read the project's `.basepack/instructions.md` for its explicit config and Python. Invoke that Python with `-m basepack --config <absolute-config> memory ...`. The local SurrealDB server must already be running; keep its data in this project. Credentials come from the configured environment variable. `guide` prints this file's installed location; action help describes arguments.

At task start or continuation, run `brief --task <goal>`. Keep current `mandatory` content directly; stale mandatory information remains an obligation to recheck, not a current fact. Use relevant and exploration hints to notice missing premises. Check coverage and open the original when a fact matters.

## Retrieve in one delegation

The working agent may delegate the question, project scope and content budget once to a subscription worker. That worker completes retrieval and scoring, then returns usable content and sources:

1. Run `search --text <terms>` across file/section summaries and original chunks. Chinese word segmentation is not substring matching; use explicit `--literal` for exact substrings, identifiers or missed proper names.
2. Use `neighbors <id>` to expand parents, children and semantic edges; follow evidence member IDs and use `read <member-id>` to verify original ranges and conditions. Search again when needed. Structural links are different from semantic claims. Read the returned content before scoring.
3. Write a JSON array of actual candidates with `id`, `kind`, `path`, `revision`, `start_line`, `end_line`, `title`, `text`, numeric `score` and a short reason. Use a common 0–100 relevance scale; a lexical/vector score is not an agent score.
4. Run `rank --input <scored.json> --budget <text-characters>`. Return the selected content, source locators and unresolved gaps. Budget omissions retain reading pointers; whole evidence is not silently truncated. The working agent may read more freely.

Use a cheaper available worker for routine retrieval. Record its actual model when available; do not invent usage or price. Keep intermediates under this project's `.basepack/memory/`, uniquely named per batch so concurrent chats do not overwrite each other's work.

## Read and maintain together

1. Run `changes --scope <explicit-files-or-directories>` after edits or when checking freshness. Fast checks use metadata; `--deep` hashes originals when a deeper check is needed.
2. Run `prepare --paths <affected-files-and-related-material> --output <reading.json>`. Read the new/old numbered originals together with relevant neighbors. Reading units are location hints. Decide the final semantic chunk boundaries, file/section summaries, knowledge nodes and semantic edges during this same reading, including conditions and evidence. Preserve original wording inside chunks.
3. Write one batch and run `apply --batch <batch.json>`. Reuse stable IDs for unchanged members. The program checks source versions, writes native records/relations transactionally, preserves snapshots/corrections and invalidates affected dependencies. A source changed during the work requires another reading of that batch; preserve actual errors.
4. Search/read the changed knowledge and ensure old conclusions are no longer current. Report uncovered ranges and any remaining stale knowledge. A prepared task pack or node count does not prove semantic work happened.

Batch fields:

- `expected`: copy this object unchanged from prepare. It holds the knowledge versions read for existing members/nodes/edges. Apply checks only targets changed by this batch; a stale draft fails explicitly, while unrelated writes remain possible. Missing expected versions permit new records only.
- `sources`: `{path, revision}` from prepare; an accepted missing source adds `deleted:true` and its previous revision.
- `members`: `{id, kind, path, parent, start_line, end_line, title, text, evidence, mandatory, coverage_gaps}`. Kinds are `file`, `section`, `chunk`; line ranges are 1-based and inclusive. Parent/evidence values are stable member IDs. Summary evidence names the chunks it covers; chunk text is exact original text. Mark only explicitly required startup information mandatory.
- `nodes`: optional `{id, kind, text, evidence}` for entities, decisions and conditions.
- `edges`: optional `{id, in, out, kind, text, conditions, evidence}`. Endpoints name `member:<id>` or `node:<id>`; evidence names member IDs read together. Edit an existing edge by its ID; adding one preserves other edges.
- `delete_members`, `delete_nodes`, `delete_edges`: explicit IDs retired by this batch. `corrections`: `{id, target, reason}`; the program captures the previous record.
- `context`: actual available `chat`, `turn`, `root_chat`; leave unavailable fields absent.

For broad maintenance, use a coordinator and at most four cheaper readers per coordinator. Merge cross-worker candidates and read both ends together before accepting a relation. Batch review is optional. Deep maintenance may revisit old or randomly selected material to seek missed relations; do not claim every pair was examined.

Back up with SurrealDB's native export and restore into a separate project directory. Include this project's configuration, original documents/images and required derived assets. Database exports preserve explicitly stored knowledge/history; vector indexes can be rebuilt from retained representations.
