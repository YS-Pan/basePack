# basePack

basePack gives agents project-local memory, shared compute coordination, and independent skills for collaboration, file organization, and engineering decisions.

| Capability | Purpose | Requirements |
| --- | --- | --- |
| Project memory | Store summaries, source excerpts, images, and relations; query published knowledge and maintain it separately | Python 3.13+ client, a separate SurrealDB 4 instance per project, and a shared CPU/CUDA embedding service |
| Resource coordination | Reuse text/image embedding across projects and submit ordinary heavy jobs | CPU/CUDA embedding service; HTCondor for jobs |
| agent-team | Choose solo work, direct collaboration, or layered teams for each task | A host with skills and subscription-based agents |
| file-structure | Organize project files by purpose and lifecycle | A host with skills |
| engineering-judgment | Judge contracts, responsibilities, compatibility, and the work passed to users | A host with skills |

The current source targets **0.9.1, in development**, for Windows and Python 3.13+. The host's subscription-based agents understand material, build relations, and score results; basePack requires no separate LLM API. Prepare the facilities needed by your chosen capability. Current fixes, installation evidence, and remaining verification are recorded in the [consistency review progress](devDoc/archive/20261111-consistency-review/progress.md).

**basePack is under development. Real use also serves as testing; record problems so they can inform subsequent fixes.**

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

Development wheels are available from [GitHub Releases](https://github.com/YS-Pan/basePack/releases). To build a normal wheel from the current source, see the [route README](experiments/20261106-basepack/README.md#development-checks-and-builds). For an existing project, follow the [upgrade steps](experiments/20261106-basepack/docs/setup-project.md#版本升级) to back up its data and refresh its entry point.

## Enable project memory

1. Follow [project setup](experiments/20261106-basepack/docs/setup-project.md) to create a minimal machine configuration and run `init` for your project. New projects default to `vector`; `hybrid` is also available. The default `doctor` checks core facilities.
2. Follow [project SurrealDB setup](experiments/20261106-basepack/docs/administrator.md#项目-surrealdb) to select a separate directory and loopback IP/port, prepare its password file once, start an authenticated server, and check `/ready`.
3. Follow [shared model deployment](experiments/20261106-basepack/docs/administrator.md) to prepare a CPU or CUDA embedding service, set its endpoint in the machine configuration, and verify one embedding request. Memory does not require HTCondor.
4. Follow the [new-shell steps](experiments/20261106-basepack/docs/setup-project.md#新-shell-接续), run `memory init` and `memory brief`, then complete the [minimal read/write workflow](experiments/20261106-basepack/docs/memory.md#最小闭环示例). New shells and chats follow the generated `AGENTS.md → .basepack/instructions.md` entry to run a brief directly. The client reads the configured password file automatically; no shell variable is needed.

Default background maintenance covers the managed project, including Git-tracked and nonignored untracked files, explicit includes, registered sources, historical pending work, and owned Codex captures. It completes mechanical changes and returns a command for a continuing coordinator to load the shipped English prompt. The host sets the actual model before dispatch and stops the coordinator and its descendants when business work ends. Discovery boundaries and unavailable content remain explicit coverage gaps; see [maintenance](experiments/20261106-basepack/docs/memory.md#自动维护与手动维护) and [Codex chat setup](experiments/20261106-basepack/docs/setup-project.md#codex-项目聊天接入).

Each project's configuration, password file, knowledge, database, and local entry point stay in that project's ignored directories. **Project memory is not distributed with this source repository.** A new clone creates its own configuration through `init`; recover existing knowledge from that project's backup.

## Independent skills

Choose only the skills you need. [agent-team](skills/agent-team/SKILL.md), [file-structure](skills/file-structure/SKILL.md), and [engineering-judgment](skills/engineering-judgment/SKILL.md) need no Python package or database. The [resources skill](experiments/20261106-basepack/skills/resources/SKILL.md) guides use of configured resource tools.

Follow the complete [skill installation and discovery procedure](experiments/20261106-basepack/docs/setup-project.md#独立-skills-安装与发现): copy each complete directory into the target project's `.agents/skills/`, or create a junction to existing project-owned originals. Check references and the host's actual project-scoped skill list. Reuse correct installations; preserve conflicting user skills and report them. `init` and core `doctor` do not install or verify independent skills.

Invoke a discovered skill by name, such as `$agent-team`, or explicitly ask the agent to read its `SKILL.md`. Other hosts use their own skill installation mechanism. Local ignored junctions must be recreated after a fresh checkout. This repository's development junctions point to its tracked skill sources. Engineering judgment remains independently usable and is maintained through real feedback.

The wheel includes the program, configuration and entry templates, memory schema, the memory skill located by `memory guide`, and reusable English coordinator/reader prompts rendered by `memory prompt`. The three general skills, resources skill, and repository examples come from the matching source checkout. Wheel-only users can obtain these directories without reinstalling the client.

## Documentation and feedback

| Entry | Contents |
| --- | --- |
| [Route README](experiments/20261106-basepack/README.md) | Capabilities, development, builds, and tests |
| [Maintenance experiment](experiments/20261111-basepack-maintenance/README.md) | Prepared candidate for program checks, entry instructions, SQL batching, usage feedback and maintenance policy; implementation has not started |
| [Project setup](experiments/20261106-basepack/docs/setup-project.md) | Configuration, new shells, upgrades, relocation, and skill discovery |
| [Memory guide](experiments/20261106-basepack/docs/memory.md) | Initial knowledge, retrieval, small-batch maintenance, and backup |
| [Resource guide](experiments/20261106-basepack/docs/resources.md) | Text/image embedding, HTCondor jobs, and Python APIs |
| [Administrator guide](experiments/20261106-basepack/docs/administrator.md) | Official facility sources, installation, services, and capacity |
| [AGENTS.md](AGENTS.md), [implementation overview](devDoc/system/overview.md) | Development rules and current implementation |

Record problems using your project's existing conventions: symptoms, version, minimal reproduction conditions, and status; add verification after a fix. Use the [issue format](experiments/20261106-basepack/docs/setup-project.md#问题记录与反馈) to draft an issue, remove credentials and private material, then submit it to [GitHub Issues](https://github.com/YS-Pan/basePack/issues) yourself or explicitly authorize an agent to submit it.

This project's own source, skills, and documentation use the [MIT license](LICENSE). Third-party dependencies and models retain their own licenses; see the [Qwen notice](experiments/20261106-basepack/src/basepack/embedding/NOTICE.Qwen3-VL-Embedding.txt).
