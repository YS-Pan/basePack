# Independent experiment layout

Use this pattern to compare methods, prototypes, or experiment tracks whose code, dependencies, state, and results need separate ownership. An experiment unit is an independently evolving project; publishing a Python package is an optional implementation choice.

## Experiment units and runs

An experiment unit owns a method, its dependencies, and its lifecycle. A changed seed, parameter, or repetition count usually creates another run in the same unit. Create a new unit when the method, dependency, or delivery boundary evolves independently.

```text
project/
  AGENTS.md                     Shared conventions and direct entry points
  README.md                     Experiment index and shared goals
  devDoc/                       Shared decisions, plans, and conclusions
  experiments/
    YYYYMMDD-short-topic/
      .git/                     Separate-repository option; retain existing boundaries
      README.md                 Hypothesis, status, entry points, reproduction, gaps
      AGENTS.md                 Necessary experiment-local rules, when needed
      pyproject.toml            Dependency/run declarations; use the actual stack
      src/                      Code layout appropriate to the language, when needed
      tests/                    Necessary checks and small fixtures
      configs/                  Experiment configuration, when needed
      data/                     Small inputs or source/version/recovery references
      tmp/<task>/               Disposable probes, trial runs and evaluation scratch
      artifacts/                Selected evidence retained across tasks, when needed
      runs/<run-id>/            Run records deliberately kept for tracking or reproduction
      RESULTS.md                Conclusions, comparisons, failures, limits, evidence
  test-cases/                   Shared fixed inputs and evaluation protocol, if needed
  test-runs/                    Retained independent evaluations, if isolation needs it
```

Adapt the names and create only the needed parts. Each experiment owns its configuration, knowledge, databases, caches, and results. Large data, models, and environments may live outside the project, located through configuration and version information. The coordination layer keeps shared direction, the experiment index, and decision-relevant conclusions; experiments retain their run details.

Apply the shared [material lifecycle](../SKILL.md#temporary-and-retained-material) within each owning project. Prefer `tmp/` for one-off trial runs and evaluations; use stable experiment units, `runs/` and `test-runs/` for work that needs an ongoing lifecycle or retained run history.

## Choose isolation and packaging

| Condition | Approach |
| --- | --- |
| A small script can use the project environment | Group its script, configuration, inputs, and result entry point; declare dependencies through the existing mechanism |
| Independent entry points, dependencies, reuse, or distribution matter | Use the language's project declarations, code layout, and necessary tests; Python may use `pyproject.toml` and `src/package_name/` |
| A separate repository and uncommitted experiment work already exist | Preserve the repository and WIP; register its entry point in the parent and retain the existing child-repository mechanism |
| Several packages evolve together in one repository | Retain the monorepo or workspace with declared dependencies and a reproducible overall revision |
| Dependencies conflict or reproduction boundaries differ | Isolate environments as needed; explicitly share compatible environments, fixed weights, or caches |

Maintain shared code once and consume it through declared dependencies or explicit versions. Each experiment must explain dependency recovery without relying on a sibling's mutable source, database, or machine-specific links. Sharing an environment leaves project memory and business state with their owning projects.

## Entry points and evidence

The experiment README identifies its question or hypothesis, status, commands, dependencies, input identity, results, limits, and next steps. Link to relevant configuration and reports rather than duplicating them.

A run must connect its code revision, effective configuration, input identity, environment, and result location; retain seeds and hardware conditions when relevant. Reuse program-generated records. Verify the relationship between data, methods, and outputs; directories or dependency locks alone do not establish successful reproduction.

Separate benchmark inputs from answers and judge materials according to evaluation visibility requirements. Experiment runs and independent evaluation runs may have separate locations; enforce reading boundaries through the actual evaluation mechanism.

## Migrate existing experiments

Inventory each experiment's root, Git/WIP, dependencies, data locations, commands, and active process dependencies. Apply an agreed old-to-new path mapping in batches, preserving date names or stable identifiers. Check related configuration and results together, including paths, imports, commands, working directories, ignore rules, and external tool references. Use reference checks for relocation; rerun expensive experiments only when execution behavior needs validation.

Keep experiment ownership local while referencing shared weights and environments externally. If active runs depend on old paths, identify the affected parts and migrate them in a safe window; reorganize unaffected parts first. Summarize results and recovery conditions before archival. Handle deletion under the project's retention requirements and explicit cleanup scope, even for regenerable evidence.

## Sources and limits

This pattern gives independent approaches their own project boundaries, state, and evidence under `experiments`. Treat legacy layouts as structural references; use the current project's task state, authorization, and acceptance criteria. Several toolchains can support the pattern:

- The [research compendium paper](https://faculty.washington.edu/bmarwick/PDFs/Marwick-Boettiger-Mullen-2018-TAS-research-compendia.pdf) supports separating data, methods, and outputs with environment documentation; it does not require a formal package for every unit.
- [PyPA's src/flat comparison](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) explains packaging and import tradeoffs; [inline script metadata](https://packaging.python.org/en/latest/specifications/inline-script-metadata/) offers dependency declarations for small scripts.
- [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/) illustrates shared locks and dependency boundaries for packages in one repository, rather than every environment-isolation need.
- [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/#directory-structure) and [Snakemake](https://snakemake.readthedocs.io/en/stable/snakefiles/deployment.html) illustrate separate responsibilities for data stages, configuration, workflows, and results. Choose their tooling and directory conventions as needed.
