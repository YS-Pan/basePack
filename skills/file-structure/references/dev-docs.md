# Development documentation layout

Use this pattern when developers and agents need to distinguish lasting guidance, current implementation, active tasks, and history. Organize development documents by content responsibility and maintenance lifecycle; source code, user documentation, and experiments retain their own responsibilities.

## Minimal structure and responsibilities

```text
project/
  AGENTS.md                  Short rules and task-specific entry points
  README.md                  Project introduction and getting started
  devDoc/
    project-charter.md        Goals and long-term requirements
    documentation.md          Documentation maintenance rules, when needed
    terminology.md            Ambiguous project-specific terms, when needed
    system/                   Implemented behavior, structure and environment
      overview.md             Implemented capabilities and relevant entry points
      architecture.md         Implemented structure, flows, boundaries, invariants
      environment.md          Dated environment observations and unchecked areas
      modules/                Contracts for implemented modules, when needed
    tasks/                    Plans, research, progress and results by task
      YYYYMMDD-short-topic/
        plan.md               Goal, scope, decisions, and completion criteria
        progress.md           Stage, completed work, blockers, and next steps
        result.md             Deliverables, checks, evidence, limits, when needed
        research/             Research and evidence index, when needed
    archive/                  Always present; retained finished work, may be empty
    change_log/
      major/                  One record per significant change
      minor/                  Meaningful local changes, when needed
  tmp/                        Disposable tests and scratch material; contents Git-ignored
  artifacts/                  Selected evidence and outputs retained for later review; Git-ignored
```

Keep one development-documentation tree at the project root, retaining an existing directory name in place of `devDoc`. Always keep its `archive/` directory, even when empty; use a `.gitkeep` when Git must retain it. Create other parts only for real content. Divide README and AGENTS responsibilities by their readers and entry points. A short plan can also hold progress and closure.

- Maintain lasting guidance across work stages. Update `system/` with implemented behavior; keep proposals in `tasks/`.
- For [experiment routes](experiment-packages.md), keep current system and task documents aligned with active routes. Retired routes contribute selected history to this root tree rather than separate maintained documentation.
- Use one task directory for an independent objective or major stage, with internal steps in the same plan when practical. At closure, reconcile still-applicable conclusions into `system/`, hand off remaining work, archive retained task directories intact, and repair references.
- Apply the shared [material lifecycle](../SKILL.md#temporary-and-retained-material). Make sources, methods, conditions, results, and limits reachable from a short summary; task documents retain evidence locations and generation conditions. Large retained outputs may live outside the repository; preserve original snapshots.
- Record changes as `YYYYMMDD_HHMMSS_short-description.md`, covering date, change, reason, impact, actual checks, and evidence. Follow the target project's timezone, severity levels, and changelog conventions; trivial changes may omit a record.

## Reading entry points

List paths needed for common tasks with their relevance and selection conditions. Let agents batch the relevant reads rather than turning directory depth into a mandatory sequence of tool calls.

| Task | Initial reads | Follow up when |
| --- | --- | --- |
| Understand the current state | Overview and relevant architecture sections | Module constraints or terminology matter |
| Continue a task | Progress and the relevant plan sections, together when known | The stage or evidence remains unclear |
| Diagnose the environment | Environment observations and relevant task sections | Specific configuration or historical conditions matter |
| Edit documentation | Maintenance rules and target files | Affected references or boundaries need checking |
| Verify a conclusion | Source index and known relevant reports | Original evidence is needed |

Keep required goals, permissions, and key constraints available to the agent; load other materials by task. Verify dates and evidence: `system` can be stale, `archive` can remain useful, and a work plan describes intent rather than implementation.

## Migration and acceptance

Assign each document one maintenance location by purpose. Check affected entry points, relative paths, heading anchors, original snapshots, Git attributes, and experiment references. Acceptance means a maintainer can find a current capability, an active task, and their direct evidence from the entry points, with the correct source identity and necessary information.

## Sources and limits

This pattern combines practices; the sources do not prescribe the exact tree above.

- [Diataxis](https://diataxis.fr/start-here/) distinguishes reader needs and can guide documents within `system`; its [application guide](https://diataxis.fr/how-to-use-diataxis/) supports gradual improvement from existing content.
- [PARA](https://fortelabs.com/blog/para/) informs the separation of active work and history, without defining software-package boundaries.
- [Cornell file management](https://data.research.cornell.edu/data-management/storing-and-managing/file-management/) emphasizes explicit conventions and descriptions understandable outside their original directories.
- [GitHub's README guide](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) supports concise entry points and repository-relative links.
