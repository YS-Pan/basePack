# basePack

`20261106-basepack` is the only active implementation route. The current source is the 0.8.0 development candidate, for Windows and Python 3.13+. Each project keeps its configuration, knowledge, source evidence, and job records in its own `.basepack/`; programs and models can be shared. Start with the clone, virtual environment, and installation commands in the root [README](../../README.md#install-the-lightweight-client).

This project's own source and documentation use the [MIT license](LICENSE), matching the root license. Third-party notices remain in the package.

Memory uses SurrealDB 4. File summaries, actual sections, source excerpts, and images are directly searchable graph members. Host subscription-based agents read material together to choose boundaries, summarize, interpret images, build relations, and score results. The program verifies source versions and atomically publishes knowledge with matching vectors. `search`, `brief`, and `read` only read published knowledge and its evidence snapshots. Independent maintenance preflight collects available project chat text and compares sources, completes mechanical batches, and sends remaining semantic work to a host agent. Task completion stops future unpublished work; accepted batches and collected originals remain available for continuation. New projects default to `vector` and can select `hybrid`; both use shared embedding. See the [onboarding progress](../../devDoc/tasks/20261110-onboarding-simplification/progress.md) for delivery evidence and remaining verification.

basePack is under development, and real use also serves as testing. Record problems using your project's conventions and draft an issue with the [feedback format](docs/setup-project.md#问题记录与反馈).

## Set up a capability

| Capability | Facilities and entry points |
| --- | --- |
| Project memory | Lightweight client, separate project SurrealDB, and shared CPU/CUDA embedding service; [project setup](docs/setup-project.md) → [database deployment](docs/administrator.md#项目-surrealdb) → [memory guide](docs/memory.md) |
| Text/image vectors and hybrid retrieval | Fixed model and shared CPU/CUDA service; [administrator guide](docs/administrator.md) → [resource guide](docs/resources.md) |
| Ordinary heavy jobs | HTCondor single-machine pool and site capacity configuration; [administrator guide](docs/administrator.md) → [job guide](docs/resources.md) |
| Independent skills | [Installation and discovery](docs/setup-project.md#独立-skills-安装与发现); general skills need no Python, database, or model |

Text/image embedding reuses a persistent Qwen3-VL-Embedding-2B service. Its automatic device choice prefers available CUDA, otherwise CPU. HTCondor queues ordinary jobs. Prepare facilities with the [administrator guide](docs/administrator.md). Below, `$python` is the installed client's interpreter; after setup, use the actual path recorded in project instructions:

```powershell
& $python -m basepack init --project-root '<absolute-project>' --machine-config '<absolute-machine-config>'
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' config show
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' doctor
```

Review the [database procedure](docs/administrator.md#项目-surrealdb), then start a separate project process bound only to an explicit loopback IP with authentication disabled. Check `/ready` in the next call. **Local clients have database administration access, and a malicious web page can write through a simple POST even when CORS rejects reading the response. CORS does not prevent those writes; the project UUID only prevents accidental connections.** Adoption of this candidate remains pending, and existing production instances have not migrated. Then run:

```powershell
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' memory init
& $python -m basepack memory guide
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' memory brief --task 'current task'
```

Codex hosts supply project binding and complete registered roots through the [chat setup workflow](docs/setup-project.md#codex-项目聊天接入); uncertain ownership and unavailable parts remain coverage gaps. Collection progress and vector coverage each differ from semantic acceptance.

After enabling memory, each new shell follows `.basepack/instructions.md` to run a brief directly; no password file or environment variable is needed. `memory.search_mode` is `vector` or `hybrid`; `memory search` uses it unless `--mode` overrides it. For identifiers, filenames, or exact text, use `--mode hybrid --literal`. The complete prepare/apply/search/read/neighbors workflow is in the [memory example](docs/memory.md#最小闭环示例). Project configuration, database, and knowledge remain local and are excluded from Git.

Resource tools can also be used without enabling memory:

```powershell
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' embed --text 'text to encode'
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' jobs run --spec '<job.json>'
```

Business projects reuse the models and environments. Embedding clients connect to the service; `--timeout` ends client waiting while server inference that has started may continue. Native Condor users keep using `request_gpus = 1` and `gpus_minimum_memory = <peak> MB` without installing basePack.

[Project setup](docs/setup-project.md) covers configuration, new shells, upgrades, relocation, and independent skill discovery. The [resource guide](docs/resources.md) includes Python APIs. The memory skill ships in the wheel and is located by `memory guide`; the [resources skill](skills/resources/SKILL.md), three general skills, and examples come from the source repository. `init` and core `doctor` do not install or verify independent skills.

## Development checks and builds

When developing or building from the repository root, select this route explicitly and use Python 3.13:

```powershell
$buildTemp = Join-Path (Get-Location) 'tmp/basepack-build'
New-Item -ItemType Directory -Force -Path $buildTemp | Out-Null
$env:TEMP = $buildTemp
$env:TMP = $buildTemp
$env:UV_CACHE_DIR = Join-Path $buildTemp 'uv-cache'
$route = Join-Path (Get-Location) 'experiments/20261106-basepack'
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) 'tmp/basepack-dev'
uv sync --project $route --python 3.13 --locked --extra embedding --extra dev
$devPython = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts/python.exe'
& $devPython -c "import basepack; print(basepack.__file__)"
& $devPython -m pytest -c 'experiments/20261106-basepack/pyproject.toml' 'experiments/20261106-basepack/tests' --basetemp 'tmp/basepack-pytest'
uv build --project $route --wheel --out-dir (Join-Path $route 'dist')
```

[pyproject.toml](pyproject.toml) and [uv.lock](uv.lock) own dependencies; the CUDA PyTorch source is cu128. The administrator guide covers uv sources and service setup. Source regressions must import this route's `src/basepack/`; normal-wheel validation must run outside the source tree and import the installed package. Check the actual import path first, and keep one active installation per interpreter. Development environments, build caches, and test fixtures belong in root `tmp/`; production clients and services use stable environments. Keep delivery and rollback wheels in this route's `dist/`. Build artifacts are generated locally. Author-machine wheels, models, and run evidence are excluded from Git; downloadable packages, when provided, are GitHub Release attachments.

Development rules are in root [AGENTS.md](../../AGENTS.md); current structure and deployment contracts are in [system](../../devDoc/system/overview.md) and [deployment](../../devDoc/system/deployment.md). Plans, progress, and results are maintained only in root `devDoc/`. The root [README](../../README.md) provides the project index.
