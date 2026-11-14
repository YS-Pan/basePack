---
name: file-structure
description: "Recommend or reorganize project file layouts for development documentation, experiment routes, private development context, and temporary or retained material. Use for structure decisions and requested file moves; ordinary prose or algorithm edits alone are outside scope."
---

# File structure

Choose a layout by purpose, maintenance lifecycle, and execution or delivery boundaries. Preserve working project conventions. Treat directory names as navigation clues; verify knowledge and completion from the contents.

## Temporary and retained material

- Prefer project-root `tmp/<task>/` for one-off tests, trial runs, temporary scripts, disposable fixtures, caches and intermediate outputs. Keep disposable contents Git-ignored; retain a directory placeholder only when needed.
- Assume `tmp/` contents can disappear any time after the task ends, for example through daily cleanup. Before closure, record needed conclusions in documentation and move selected material worth retaining to its stable location.
- Use `artifacts/` for selected original evidence: logs, outputs and snapshots of executed scripts, effective configuration or inputs needed for later review. Select by retention need rather than saving all temporary work.
- Maintain source, reusable configuration, regression fixtures, stable input/version references and conclusions in their version-controlled owning locations. Retention and version control are separate decisions; classify by purpose and lifetime rather than size. Keep service state, shared dependencies and deliverables in stable locations independently usable after `tmp/` is cleared.

## Choose a pattern

| Current problem | Read |
| --- | --- |
| Long-term guidance, current implementation, active work, and history are mixed | [Development documentation](references/dev-docs.md) |
| Experiment routes have tangled code, dependencies, data, or results | [Experiment routes](references/experiment-packages.md) |
| Confidential development context needs a separate local version and publication boundary | [Private context](references/private-context.md) |
| Documentation and experiment problems occur together | Read both references together and combine the layers |
| Another layout problem | Propose the smallest layout that fits its purpose, lifecycle, and execution or delivery boundaries |

Use the task and existing entry points to locate relevant directories, version-control boundaries, and materials. Batch known reads and reuse valid context. For a large repository, start with relevant indexes and retain locations for deeper reading; follow up when the findings require it.

## Propose or reorganize

For advice or review, return findings or a proposed tree and source-to-destination mapping as appropriate. Explain responsibilities, retained conventions and unresolved boundaries.

For authorized reorganization:

1. Before moving files, check source and destination paths, conflicts, nested repositories, uncommitted work, active processes, and external path dependencies.
2. Apply the path mapping within scope, preserving original evidence, version history and related attachments. Create useful files and folders plus structural directories required by the selected pattern. Treat deletion and archival according to their authorization; complete unaffected work and explain blocked moves.
3. Repair affected links, commands, configuration, imports, data locations and ignore rules. Run relevant path or lightweight execution checks, then report actual changes, checks and remaining work. Verify usability from evidence rather than directory appearance.

Keep one maintenance source for shared code and reuse it through declared dependencies or the project's module mechanism. Locate shared environments, models, and large artifacts through configuration. Keep shared assets and existing results in place unless their relocation, regeneration, or cleanup is part of the task.

## Extend the patterns

When skill maintenance is part of the task, add a useful new pattern as a reference covering its trigger, minimal tree, content and version boundaries, entry points, migration considerations and sources; add its selection condition to the table. Ordinary project advice uses the existing skill. Combine patterns as needed; project requirements and language conventions take precedence over example names.
