---
name: file-structure
description: "Recommend or reorganize project file layouts for development documentation, independent experiments, and temporary or retained material. Use for structure decisions and requested file moves; ordinary prose or algorithm edits alone are outside scope."
---

# File structure

Choose a layout by purpose, maintenance lifecycle, and execution or delivery boundaries. Preserve working project conventions. Treat directory names as navigation clues; verify knowledge and completion from the contents.

## Temporary and retained material

- Prefer the owning project's `tmp/<task>/` for one-off tests, trial runs, temporary scripts, fixtures, caches and intermediate outputs. Keep disposable contents Git-ignored; retain a directory placeholder only when needed.
- Assume `tmp/` contents can disappear any time after the task ends, for example through daily cleanup. Before closure, record needed conclusions in documentation and move selected material worth retaining to its stable location.
- Use `artifacts/` for material deliberately retained across tasks, such as evidence, inputs, scripts, logs and outputs needed for later review. Select by retention need rather than saving all temporary work.
- Keep source, durable configuration, service state, shared dependencies and deliverables in their stable owning locations, independently usable after `tmp/` is cleared.

## Choose a pattern

| Current problem | Read |
| --- | --- |
| Long-term guidance, current implementation, active work, and history are mixed | [Development documentation](references/dev-docs.md) |
| Independent approaches have tangled code, dependencies, data, or results | [Experiment units](references/experiment-packages.md) |
| Both problems occur | Read both references together and combine the layers |
| Another layout problem | Propose the smallest layout that fits its purpose, lifecycle, and independent execution or delivery boundaries; add a reference when useful |

Use the task and existing entry points to locate relevant directories, version-control boundaries, and materials. Batch known reads and reuse valid context. For a large repository, start with relevant indexes and retain locations for deeper reading; follow up when the findings require it.

## Propose or reorganize

1. Explain the layout choice, retained conventions, directory responsibilities, direct reading or execution entry points, and unresolved boundaries. Create files for actual content; combine short documents where useful.
2. For advice or planning, deliver an adapted tree and a source-to-destination mapping. For authorized reorganization, apply that mapping within scope. Treat deletion, migration, and archival according to their respective authorization.
3. Before moving files, check source and destination paths, conflicts, nested repositories, uncommitted work, active processes, and external path dependencies. Preserve originals, version history, and related attachments. Complete unaffected work and explain any blocked moves.
4. Repair affected links, commands, configuration, imports, data locations, and ignore rules. Run relevant path checks or lightweight execution checks, then report actual changes, checks, and remaining work. Verify usability and reproducibility from evidence rather than directory appearance.

Keep one maintenance source for shared code and reuse it through declared dependencies or the project's module mechanism. Locate shared environments, models, and large artifacts through configuration. Keep shared assets and existing results in place unless their relocation, regeneration, or cleanup is part of the task.

## Extend the patterns

When a new pattern has a concrete use, add a reference covering its trigger, minimal tree, content and version boundaries, reading or execution entry points, migration considerations, and sources. Add its selection condition to the table. Combine patterns as needed; project requirements and language conventions take precedence over example names.
