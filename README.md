# basePack

basePack gives agents project-local memory, shared compute coordination, and independent skills for collaboration, file organization, and engineering decisions.

## Project status

On 25 November 2026, the maintainer decided to put this project on hold and start a separate project. This repository and the existing local installation remain available to projects that use basePack for close-out. `v0.19.1` is the snapshot of the current implementation for that work. Keep each project's configuration, database, evidence, and recovery materials with the project that owns them. The [latest release](https://github.com/YS-Pan/basePack/releases/latest) provides the Windows client wheel and checksum.

The project aimed to help an agent recover evidence it knows to look for and surface important clues it had yet to consider, at a cost that fits ordinary project work. Real trials included slide production, engineering research, and a dissertation migration. Published knowledge could be searched, traced to exact source versions, and recovered from a backup in tested workflows. A slide trial also showed that a verified graph path could recover the image actually used in a finished result. The trials exposed four problems behind the decision to pause.

- **Coverage and useful relations diverged.** A library could hold thousands of members while yielding few links between an adopted output, its editable source, and its underlying data. Workers often read the two endpoints in different batches. Targeted co-reading could recover some relationships. Ordinary maintenance still struggled to pick the right outputs and sources on its own. In the dissertation trials, independent maintenance recovered 0 of 26 held-out relations under the strict criteria, including 0 of the 16 whose evidence was available in the test material. The legacy reference library remains available separately.
- **The benefit varied by task.** Direct file search and exact source reads answered some text questions with little setup. A later equal-budget comparison found an additional relationship in one run, with no demonstrated use of that relationship in the final business answer. The limited chat-index trial did verify retrieval and exact host readback for the admitted messages. Broader coverage and a repeatable gain on unseen work remain open.
- **End-to-end maintenance was expensive.** Waiting for agents, encoding, publishing, recovering failed batches, and checking source readback all added time. One engineering case took roughly seven hours to do the original work. Follow-on maintenance for the same results had a recorded lower bound above 26 hours across attempts, with coverage still incomplete. That elapsed time includes mixed work and waits. Reduced file-summary counts alone did not establish a speedup.
- **Deployment and follow-through required hands-on attention.** Windows database startup and embedding readiness could time out. Host sandbox and approval boundaries could interrupt chat collection or cross-chat follow-up. Publication sometimes needed repairs to source ranges, version references, or privacy metadata. Some trial failures went unretested until a coordinator assigned the repair and checked it from the normal entry point. Keeping the growing implementation, tests, and agent instructions aligned added maintenance work while the gains on ordinary tasks remained uneven.

**Follow-up trials with different maintenance models.** Two projects each supplied five related files. In each project, four independent teams started from empty databases and used basePack `v0.19.1` to maintain identical copies of those files. Each team had one coordinator and one reader. The table counts the cross-file relations each team authored and published.

| Coordinator | Reader | Array reconstruction | Dual-arm S21 calibration |
| --- | --- | ---: | ---: |
| GPT-6.1 Terra Ultra | GPT-6 Luna Max | 4 | 4 |
| GPT-6.1 Terra Ultra | GPT-6.2 Sol Max | 4 | 5 |
| GPT-6.2 Sol Max | GPT-6 Luna Max | 0 | 4 |
| GPT-6.2 Sol Max | GPT-6.2 Sol Max | 7 | 5 |

Switching both roles to Sol produced more relations than the default Terra/Luna pair on both samples. In array reconstruction, switching only the reader left the count at four, and switching only the coordinator yielded zero. In calibration, switching the reader added one relation with either coordinator. Both Sol readers linked the documented configuration-check command to the baseline file it reads. The Sol readers also produced fewer memory entries than the Luna readers in calibration and more in array reconstruction. Each combination ran once per sample. Retrieval accuracy and run-to-run variability remain unmeasured.

The last trials point to smaller tests drawn from real maintenance backlogs. Each test can start from a concrete output, compare directory search and direct reading with the indexed workflow on a held-out question, and keep verified results for later use. Measure the time through successful readback. The [project setup](experiments/20261106-basepack/docs/setup-project.md) and [memory guide](experiments/20261106-basepack/docs/memory.md) remain the entry points for existing projects.

| Capability | Purpose | Requirements |
| --- | --- | --- |
| Project memory | Store summaries, source excerpts, images, and relations; query published knowledge and maintain it separately | Python 3.13+ client, a separate SurrealDB 4 instance per project, and a shared CPU/CUDA embedding service |
| Resource coordination | Reuse text/image embedding across projects and submit ordinary heavy jobs | CPU/CUDA embedding service; HTCondor for jobs |
| agent-team | Choose solo work, direct collaboration, or layered teams for each task | A host with skills and subscription-based agents |
| file-structure | Organize project files by purpose and lifecycle | A host with skills |
| engineering-judgment | Design data models, module boundaries, and failure handling around explicit contracts | A host with skills |

The client supports Python 3.13+ on Windows. The [deployment contract](devDoc/system/deployment.md) describes facility requirements. The host's subscription-based agents understand material, build relations, and score results. basePack requires no separate LLM API. Prepare the facilities needed by your chosen capability.

## Install the lightweight client

Install Git and Python 3.13 or 3.14, then run in PowerShell (this example uses 3.13):

```powershell
git clone https://github.com/YS-Pan/basePack.git
Set-Location basePack
py -3.13 -m venv .venv
$python = (Resolve-Path '.venv/Scripts/python.exe').Path
& $python -m pip install './experiments/20261106-basepack'
& $python -c "from importlib.metadata import version; print(version('basepack'))"
```

The Python package lives in `experiments/20261106-basepack`; include that directory when installing from the repository root. These commands install the lightweight client. Project memory connects to a shared model service whose dependencies belong in its service environment. General skills can be used independently. This virtual environment belongs to the current clone; after moving or deleting it, recreate the client and update project instructions.

To build a wheel from source, see the [route README](experiments/20261106-basepack/README.md#development-checks-and-builds). The 0.19 series uses memory schema 4. Existing schema 3 libraries require the [offline graph migration](experiments/20261106-basepack/docs/setup-project.md#升级到-019-的统一图) before switching clients. The optional `behavior` extra installs the KL-NMF training dependencies. Basic retrieval can use the lightweight client.

## Enable project memory

1. Follow [project setup](experiments/20261106-basepack/docs/setup-project.md) to create a minimal machine configuration, collect the host's subagent limit and source, and run `init` for your project. New projects default to `vector`; `hybrid` is also available. The default `doctor` checks core facilities.
2. Follow [project SurrealDB setup](experiments/20261106-basepack/docs/administrator.md#项目-surrealdb) to select a separate directory and loopback IP/port, prepare its password file once, start an authenticated server, and check `/ready`.
3. Follow [shared model deployment](experiments/20261106-basepack/docs/administrator.md) to prepare a CPU or CUDA embedding service, set its endpoint in the machine configuration, and verify one embedding request. Memory does not require HTCondor.
4. Follow the [new-shell steps](experiments/20261106-basepack/docs/setup-project.md#新-shell-接续), run `memory init` and one `memory brief` for the task, then complete the [minimal read/write workflow](experiments/20261106-basepack/docs/memory.md#最小闭环示例). Later shells initialize their command parameters and continue the same task. The client reads the configured password file automatically.

Each task keeps its brief. Tasks intuitively expected to take at most ten minutes skip automatic maintenance entirely; longer tasks start one whole-project run alongside business work, reassessing if scope grows. Dispatched subtasks follow their briefs. Maintenance acquires one owner. The 0.18 source uses a finite local task pool and a small fixed Luna pool: Terra plans and ends its first turn, the parent confirms idle then seals and sends go, and the last normal worker resumes the same Terra for sole publication. The parent retains the resume seat and closes the wave after actual host outcomes. Retrieval has a separate dispatch entry and needs no maintenance owner. Authors choose semantic content; the program compiles hash-pinned prepare proposals and publishes atomically. Successful publication completes an ordinary batch; full maintenance reports its authorized coverage and remainders. The host stops its owner, cancels its agents and releases after publication ends. See [maintenance and feedback](experiments/20261106-basepack/docs/memory.md#自动维护与手动维护) and [Codex chat setup](experiments/20261106-basepack/docs/setup-project.md#codex-项目聊天接入).

`memory publish` and its Python helper combine completed-draft hash checks, freeze/validation and apply; an existing frozen batch can resume with its original identity. Agents freely compose the other atomic tools and make grouping or revision decisions. CUDA embedding explicitly uses cuDNN attention with a 32768-token per-item limit; `gpu_memory_mib` is a soft target, with 9216 MiB as the machine-template example. Legal inputs can still exhaust memory. See the [memory](experiments/20261106-basepack/docs/memory.md#最小闭环示例) and [resource](experiments/20261106-basepack/docs/resources.md#共享-embedding) guides.

Each project's configuration, password file, knowledge, database, and local entry point stay in that project's ignored directories. **Project memory is not distributed with this source repository.** A new clone creates its own configuration through `init`; recover existing knowledge from that project's backup.

Collect Codex originals independently with `memory collect`. A bound project then chooses `memory maintain --collection <receipt>` or explicitly `--retained`; retained originals leave current chat freshness unknown. Explicit `--scope` restricts the actual workset, including registered and missing sources. Authors own finite related source groups and shared graph targets. Finite waves retain the same receipt/owner/control, fixed references and explicit notification outcomes; pool execution does not establish publication or full maintenance completion. Optional `memory.private_scope` classifies files in place without expanding discovery; large source snapshots retain complete text through bounded transactional messages. See the [memory guide](experiments/20261106-basepack/docs/memory.md).

`memory brief` reads mandatory information, bounded overview entries and known gaps without searching or contacting the model. `memory retrieve --question '...'` prepares a whole-project request and host dispatch. The worker fixes independent base anchors before behavioral candidates, reads evidence, scores once and saves a generated receipt; the host records it after actual delivery. Pure co-delivery KL-NMF and per-anchor Gaussian similarity provide access intervals with no calendar decay. Low-weight knowledge remains retrievable and retained; `rank` only sorts, deduplicates and applies the budget. See the [memory guide](experiments/20261106-basepack/docs/memory.md).

Confidential development context can live in a project-root `private/` with its own local Git repository, excluded from public Git and releases. Memory automatically discovers that repository's tracked and nonignored files within the same project and carries a `private` boolean through version-pinned provenance. Public documents remain self-contained with optional private references. Full recovery backups remain private; the marker does not make a raw database export safe to publish. See the [private-context pattern](skills/file-structure/references/private-context.md).

## Independent skills

Choose only the skills you need. [agent-team](skills/agent-team/SKILL.md), [file-structure](skills/file-structure/SKILL.md), and [engineering-judgment](skills/engineering-judgment/SKILL.md) need no Python package or database. The [resources skill](experiments/20261106-basepack/skills/resources/SKILL.md) guides use of configured resource tools; [basepack-setup](experiments/20261106-basepack/skills/basepack-setup/SKILL.md) guides installation and upgrades.

Follow the complete [skill installation and discovery procedure](experiments/20261106-basepack/docs/setup-project.md#独立-skills-安装与发现): copy each complete directory into the target project's `.agents/skills/`, or create a junction to existing project-owned originals. Check references and the host's actual project-scoped skill list. Reuse correct installations; preserve conflicting user skills and report them. `init` and core `doctor` do not install or verify independent skills.

Invoke a discovered skill by name, such as `$agent-team`, or explicitly ask the agent to read its `SKILL.md`. Other hosts use their own skill installation mechanism. Local ignored junctions must be recreated after a fresh checkout. This repository's development junctions point to its tracked skill sources. Engineering judgment remains independently usable and is maintained through real feedback.

The wheel includes the program, configuration and entry templates, memory schema, the memory skill located by `memory guide`, and reusable English role prompts: `memory prompt` renders the sole coordinator, while `memory wave worker-prompt` and `memory wave task-prompt` render Luna's wave and claimed-task instructions. The three general skills, resources skill, and repository examples come from the matching source checkout. Wheel-only users can obtain these directories without reinstalling the client.

## Documentation and feedback

| Entry | Contents |
| --- | --- |
| [Route README](experiments/20261106-basepack/README.md) | Capabilities, development, builds, and tests |
| [Project setup](experiments/20261106-basepack/docs/setup-project.md) | Configuration, new shells, upgrades, relocation, and skill discovery |
| [Configuration maintenance](experiments/20261106-basepack/docs/project-config-maintenance.md) | Changes to host capacity, paths, models, services, and project state |
| [Memory guide](experiments/20261106-basepack/docs/memory.md) | Initial knowledge, retrieval, small-batch maintenance, and backup |
| [Resource guide](experiments/20261106-basepack/docs/resources.md) | Text/image embedding, HTCondor jobs, and Python APIs |
| [Administrator guide](experiments/20261106-basepack/docs/administrator.md) | Official facility sources, installation, services, and capacity |
| [AGENTS.md](AGENTS.md), [implementation overview](devDoc/system/overview.md) | Development rules and current implementation |

Record problems using your project's existing conventions: symptoms, version, minimal reproduction conditions, and status; add verification after a fix. Use the [issue format](experiments/20261106-basepack/docs/setup-project.md#问题记录与反馈) to draft an issue, remove credentials and private material, then submit it to [GitHub Issues](https://github.com/YS-Pan/basePack/issues) yourself or explicitly authorize an agent to submit it.

This project's own source, skills, and documentation use the [MIT license](LICENSE). Third-party dependencies and models retain their own licenses; see the [Qwen notice](experiments/20261106-basepack/src/basepack/embedding/NOTICE.Qwen3-VL-Embedding.txt).
