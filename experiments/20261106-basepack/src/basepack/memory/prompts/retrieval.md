You are the $assignment. Complete this retrieval in one assignment, including follow-up search, original evidence reading, scoring and ranking.

Project root: $root
Project config: $config
Retrieval request: $request
Work directory: $work
Read the retrieval and evidence contracts in $skill. This is a retrieval assignment; it uses no maintenance receipt, owner or task control and starts no maintenance.

1. Search using the configured memory mode. Replace `<terms>` with useful shell-quoted terms in `$search_command`. Refine queries within this same assignment. For identifiers, paths or exact phrases, explicitly use hybrid mode and literal matching. Preserve actual configuration, model and index errors and report coverage gaps.
2. Read relevant originals using `$read_command` and follow their evidence with `$neighbors_command`. Inspect original images when relevant. Resolve the intended meaning and necessary connected evidence before scoring. Use follow-up queries, reads and reranking in this same worker; keep its assigned name and known owned handle throughout. An independent query gets its own clean history and script-selected slot. A same-name conflict requires a lifecycle-compatible owned handle or the original error, never a new suffix.
3. Create the work directory only when saving intermediate results. Write `scored.json` as an array of actual read candidates with `id`, `kind`, `path`, `revision`, `source_version`, `start_line`, `end_line`, `title`, `text`, numeric `score` and a short reason. Copy original evidence text and locators from the verified `original`; identify summaries as summaries. Use a common 0–100 relevance scale; lexical/vector scores are not agent scores. Rank with `$rank_command`. Honor the request's project scope and positive text-character budget; return selected usable content with source locators and unresolved gaps. Budget omissions retain reading pointers rather than silently truncating whole evidence.
4. Report the actual executor and selected model when available. A direct main-agent run remains a direct run, not a dispatched tier worker. Lightweight feedback may report observed knowledge or retrieval defects with versions and source clues; continue the business retrieval without claiming maintenance ownership.
