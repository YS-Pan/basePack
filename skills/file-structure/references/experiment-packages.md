# Experiment routes and runs

Use this pattern for candidate methods, prototypes, or implementations pursuing one project's goal. An experiment is a route within the project. Usually keep only the latest route active; compare a few briefly and converge on one. Routes that need sustained independent development belong in separate projects.

## Project, experiment and run

An experiment groups a route's code, dependencies, configuration and stable inputs. A changed seed, parameter, or repetition count usually creates another run of that route. Publishing an installable package is optional.

```text
project/
  AGENTS.md                     Project conventions and direct entry points
  README.md                     Goal, active route and experiment index
  devDoc/                       Public documentation for the active route
    archive/                    Always present; may be empty
  experiments/
    YYYYMMDD-short-topic/
      README.md                 Route identity, commands and links to project docs
      pyproject.toml            Dependency/run declarations; use the actual stack
      src/                      Code layout appropriate to the language, when needed
      tests/                    Maintained checks and versioned regression fixtures
      configs/                  Experiment configuration, when needed
      data/                     Stable inputs or source/version/recovery references
  evaluation/                   Shared evaluation inputs, protocol and code, when needed
  tmp/<task>/                   One-off runs, evaluations and other disposable work
  artifacts/runs/<run-id>/      Selected run and evaluation evidence retained for review
```

Adapt names and create parts as needed, while keeping `devDoc/archive/` present even when empty. Preserve existing experiment names or use creation dates and stable route identifiers. Project knowledge, databases and task state remain with the project; large data, models and environments may be external, located through configuration and recovery information.

Apply the shared [material lifecycle](../SKILL.md#temporary-and-retained-material). Use the project-root `tmp/` by default for trial runs and evaluations, and select retained evidence into project-root `artifacts/runs/`. A run may refer to one or several experiments; evaluation is a run purpose, not a separate output hierarchy.

Use the [development documentation layout](dev-docs.md) once at the project root as the public maintenance source. Confidential originals, derivatives and evidence use the [private context](private-context.md) boundary. Keep current implementation, plans and progress focused on active work. When a route ends, preserve useful conclusions and switch reasons in root history, update current documents, and link them from experiment READMEs. Experiment folders hold their implementation and brief entry points; maintain detailed plans, progress and results in root `devDoc/`.

## Choose isolation and packaging

| Condition | Approach |
| --- | --- |
| A disposable probe can use the project environment | Keep it in root `tmp/`; declare required dependencies through the existing mechanism |
| A route needs distinct entry points, dependencies, reuse, or distribution | Use the language's declarations, code layout and necessary tests; Python may use `pyproject.toml` and `src/package_name/` |
| A separate repository and uncommitted experiment work already exist | Preserve Git/WIP and register the entry point; change repository boundaries only within the authorized migration scope |
| Dependencies conflict or reproduction boundaries differ | Isolate environments as needed; explicitly share compatible environments, fixed weights, or caches |

Maintain shared code once and consume it through declared dependencies or explicit versions. Recover a route's dependencies without relying on another experiment's mutable source, database, or machine-specific links. Use existing repository/workspace mechanisms where appropriate; the default tree does not require nested repositories.

## Entry points and evidence

The project README identifies the active route and links to current documentation. Each experiment README gives its question, entry points and dependency/input references, then links to the relevant root plans and results. Keep detailed status and conclusions in that one documentation set.

A retained run connects its experiment identity, code revision, effective configuration, input identity, environment and result location; retain seeds and hardware conditions when relevant. Reuse program-generated records rather than imposing another schema. Keep maintained code, configurations, fixtures and recovery references in their versioned stable locations; selected execution snapshots, logs and outputs belong in `artifacts/runs/`.

Keep shared evaluation inputs, protocol and evaluation code in `evaluation/`. Separate inputs from answers and judge materials according to visibility requirements, enforced by the evaluation mechanism. Selected evaluation outputs use the same `artifacts/runs/` location as other runs.

## Migrate existing experiments

Inventory each experiment's root, Git/WIP, dependencies, data locations, commands, and active process dependencies. Apply an agreed old-to-new path mapping in batches, preserving date names or stable identifiers. Check related configuration and results together, including paths, imports, commands, working directories, ignore rules, and external tool references. Use reference checks for relocation; rerun expensive experiments only when execution behavior needs validation.

Keep project state local while referencing shared weights and environments externally. If active runs depend on old paths, migrate those parts in a safe window and reorganize unaffected parts first. Before retiring a route, reconcile the root documentation and preserve needed results and recovery conditions. Handle deletion and any project split within the authorized scope.

## Sources and limits

This pattern separates candidate implementations while keeping one active development direction and one public documentation set per project. The active-route and material-location choices are project conventions; the sources below inform code, data and dependency organization rather than prescribing that exact tree. Treat legacy layouts as structural references and use the current project's task state, authorization and acceptance criteria.

- The [research compendium paper](https://faculty.washington.edu/bmarwick/PDFs/Marwick-Boettiger-Mullen-2018-TAS-research-compendia.pdf) supports separating data, methods, and outputs with environment documentation; it does not require a formal package for every unit.
- [PyPA's src/flat comparison](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) explains packaging and import tradeoffs; [inline script metadata](https://packaging.python.org/en/latest/specifications/inline-script-metadata/) offers dependency declarations for small scripts.
- [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/) illustrates shared locks and dependency boundaries for packages in one repository, rather than every environment-isolation need.
- [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/#directory-structure) and [Snakemake](https://snakemake.readthedocs.io/en/stable/snakefiles/deployment.html) illustrate separate responsibilities for data stages, configuration, workflows, and results. Choose their tooling and directory conventions as needed.
