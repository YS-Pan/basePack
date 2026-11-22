# basePack

`20261106-basepack` is the only active implementation route. See [pyproject.toml](pyproject.toml) for the current development version. The route targets Windows and Python 3.13+. Each project keeps its configuration, knowledge, source evidence, and job records in its own `.basepack/`; programs and models can be shared. Start with the root [installation commands](../../README.md#install-the-lightweight-client). The 0.19 development candidate initializes new memory stores with schema 4 and member identity 2. Existing schema 3 installations require an explicit offline migration before switching to the new graph. See [redesign progress](../../devDoc/tasks/20261122-memory-graph-redesign/progress.md) and the actual installed state in the [deployment contract](../../devDoc/system/deployment.md).

This project's own source and documentation use the [MIT license](LICENSE), matching the root license. Third-party notices remain in the package.

Memory uses SurrealDB 4. Host subscription agents read originals, choose boundaries, summarize, build relations and score results. The program compiles proposals from hash-pinned prepare packages and publishes knowledge with matching vectors in one native transaction. `search`, `brief`, and `read` query published knowledge only. Keep brief for every task; intuitively short tasks (at most ten minutes) skip automatic maintenance, while longer tasks start one whole-project run and reassess when scope expands. The 0.18 source uses a finite local task pool: Terra plans a wave, fixed Luna workers claim tasks repeatedly, and the last normal worker resumes the same Terra for compilation and sole publication. The parent confirms Terra is idle before sealing and sending go, reserves its resume seat, and closes the wave after the final host outcomes. Pool size follows work rather than filling capacity; no extra coordinator is added to read alone. Retrieval dispatch is independent of maintenance ownership. Successful publication completes an ordinary batch; full maintenance reports its authorized coverage and remainders; use feedback waits for the next owner and an audit requires explicit user intent. At business completion stop, cancel descendants and release after publication ends. New projects default to `vector` and can select `hybrid`. See the [memory guide](docs/memory.md).

`memory publish` shares one implementation with the Python helper: verify ordered completed-draft hashes, freeze/validate, save the fixed batch and apply. Resume an existing frozen batch with the same batch ID and UUIDs; the database receipt remains authoritative if its local result projection fails. Agents use existing atomic tools and ordinary Python for other preparation, grouping and revision decisions; see the [publication example](docs/memory.md#最小闭环示例).

`memory collect` independently preserves Codex originals. Bound projects maintain with `--collection <receipt>` or explicit `--retained`; retained originals leave current chat freshness unknown. `--scope` restricts the actual workset, including registered and missing sources. Authors own finite semantic groups and shared graph targets, then deliver fixed references. `memory wave create --readers N` fixes a small reader pool under the same receipt and owner/control. Tasks separate accepted source paths from extra read-only evidence, and fixed drafts, notification outcomes and publication intents remain recoverable. Execution, publication and maintenance completion are distinct. See [finite-wave maintenance](docs/memory.md#有限任务池与两段式-terra); installation and the real host loop remain pending.

Large text snapshots are split into bounded statements inside one native transaction and remain complete originals on readback and export. Optional `memory.private_scope` classifies selected files in place, without expanding discovery; the root `private/` remains private. Frozen rules and versioned markers preserve historical classification and reuse unchanged vectors. See [private sources](docs/memory.md#私有资料与分享边界).

basePack is under development, and real use also serves as testing. Record problems using your project's conventions and draft an issue with the [feedback format](docs/setup-project.md#问题记录与反馈).

Brief reads mandatory information, bounded cross-source overview entries and explicit gaps without search or embedding. `memory retrieve --question '...'` prepares a whole-project request with a 6000-character default budget and stable delivery identity. The worker fixes base anchors with `retrieval-start` and uses bounded multi-hop `graph-query` rounds. It reads the exact evidence, scores independently and creates a receipt with the fixed anchors and observed versions. The host confirms the actual delivery. Co-delivery KL-NMF and per-anchor Gaussian similarity supply access intervals. Low-weight knowledge stays available for base retrieval. Empty first deliveries advance fact J, nonempty ones also advance opportunity C, and retries advance neither. Recovery follows [configuration maintenance](docs/project-config-maintenance.md#按变化边界准备恢复集合).

## Set up a capability

| Capability | Facilities and entry points |
| --- | --- |
| Project memory | Lightweight client, separate project SurrealDB, and shared CPU/CUDA embedding service; [project setup](docs/setup-project.md) → [database deployment](docs/administrator.md#项目-surrealdb) → [memory guide](docs/memory.md) |
| Text/image vectors and hybrid retrieval | Fixed model and shared CPU/CUDA service; [administrator guide](docs/administrator.md) → [resource guide](docs/resources.md) |
| Ordinary heavy jobs | HTCondor single-machine pool and site capacity configuration; [administrator guide](docs/administrator.md) → [job guide](docs/resources.md) |
| Independent skills | [Installation and discovery](docs/setup-project.md#独立-skills-安装与发现); general skills need no Python, database, or model |

Text/image embedding reuses a shared Qwen3-VL-Embedding-2B service. Automatic device selection prefers CUDA, which uses cuDNN attention, and falls back to CPU when CUDA is unavailable. The per-item limit is 32768 actual tokens including templates, instructions and image tokens. Inputs exceeding the token limit are rejected before inference. `gpu_memory_mib` is an adjustable soft target, with 9216 MiB in the template. Text starts at batch 4 and requests containing images use batch 1. CUDA clears unused allocator cache after 60 seconds idle. The Windows user task stops the service after 30 minutes idle and can reload the same model on demand. See the [resource contract](docs/resources.md#共享-embedding).

HTCondor queues ordinary jobs. Prepare facilities with the [administrator guide](docs/administrator.md). The setup agent obtains the effective host limit, normalized to subagents excluding the main agent and including all descendants; replace `<C>` and its source below. `$python` is the installed client's interpreter; after setup, use the actual path recorded in project instructions:

```powershell
& $python -m basepack init --project-root '<absolute-project>' --machine-config '<absolute-machine-config>' --max-concurrent-subagents <C> --concurrency-source '<effective host config and counting basis>'
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' config show
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' doctor
```

Follow the [database procedure](docs/administrator.md#项目-surrealdb) to prepare one password file and start an authenticated server bound to loopback. Windows user tasks support a fixed port or `http://127.0.0.1:0`, with optional idle shutdown. For a managed task, `runtime start memory` waits for readiness and reports the actual address. The client reads the same password file automatically. Then run:

```powershell
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' memory init
& $python -m basepack memory guide
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' memory brief --task 'current task'
```

Codex hosts supply project binding and complete registered roots through the [chat setup workflow](docs/setup-project.md#codex-项目聊天接入); uncertain ownership and unavailable parts remain coverage gaps. Collection progress and vector coverage each differ from semantic acceptance.

After enabling memory, run brief once at task startup using `.basepack/instructions.md`; later shells initialize the command parameters and retain that task's brief. The client reads its password file automatically. `memory.search_mode` is `vector` or `hybrid`; `memory search` uses it unless `--mode` overrides it. For identifiers, filenames, or exact text, use `--mode hybrid --literal`. The complete publish/search/read/neighbors workflow is in the [memory example](docs/memory.md#最小闭环示例). Project configuration, password file, database, and knowledge remain local and are excluded from Git.

Resource tools can also be used without enabling memory:

```powershell
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' embed --text 'text to encode'
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' jobs run --spec '<job.json>'
```

Business projects reuse the models and environments. Embedding clients connect to the service; `--timeout` ends client waiting while server inference that has started may continue. Native Condor users keep using `request_gpus = 1` and `gpus_minimum_memory = <peak> MB` without installing basePack.

[Project setup](docs/setup-project.md) covers new shells, upgrades, relocation, and independent skill discovery. Read [configuration maintenance](docs/project-config-maintenance.md) when installing, upgrading or changing project/host settings. The [resource guide](docs/resources.md) includes Python APIs. The memory skill and English role prompts ship in the wheel, accessed through `memory guide`, the sole-coordinator `memory prompt`, Luna's `memory wave worker-prompt` / `memory wave task-prompt`, and `memory retrieval-prompt`; the [resources skill](skills/resources/SKILL.md), three general skills, and examples come from the source repository. `init` and core `doctor` do not install or verify independent skills.

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
uv sync --project $route --python 3.13 --locked --extra embedding --extra behavior --extra dev
$devPython = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts/python.exe'
& $devPython -c "import basepack; print(basepack.__file__)"
& $devPython -m pytest -c 'experiments/20261106-basepack/pyproject.toml' 'experiments/20261106-basepack/tests' --basetemp 'tmp/basepack-pytest'
uv build --project $route --out-dir (Join-Path $route 'dist')
```

[pyproject.toml](pyproject.toml) and [uv.lock](uv.lock) own dependencies; the CUDA PyTorch source is cu128. The administrator guide covers uv sources and service setup. Build the sdist and then its wheel with the default command above ([uv build](https://docs.astral.sh/uv/concepts/projects/build/)); direct incremental `--wheel` builds with this backend can retain deleted files from `build/lib`. Compare package file names and bytes with source before accepting a wheel. Source regressions must import this route's `src/basepack/`; normal-wheel validation must run outside the source tree and import the installed package. Check the actual import path first, and keep one active installation per interpreter. Development environments, build caches, and test fixtures belong in root `tmp/`; production clients and services use stable environments. Keep delivery and rollback wheels in this route's `dist/`. Build artifacts are generated locally. Author-machine wheels, models, and run evidence are excluded from Git; downloadable packages, when provided, are GitHub Release attachments.

Development rules are in root [AGENTS.md](../../AGENTS.md); current structure and deployment contracts are in [system](../../devDoc/system/overview.md) and [deployment](../../devDoc/system/deployment.md). Public plans, progress, and results are maintained in root `devDoc/`; optional confidential source material and analysis live in the separate ignored `private/` tree. The root [README](../../README.md) provides the project index.
