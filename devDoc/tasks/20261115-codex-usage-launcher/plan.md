# Codex 用量统计目录与运行行为整改计划

2026-11-15 修订。状态：计划已按用户新方向重写，尚未实施；CLI 默认方案待选择。本文替代此前“原项目启动器把报告写回开发目录”的方案，历史版本在 Git `1d63cb3`。执行状态见 [progress.md](progress.md)。

## 目标与已定边界

- `D:/project/trifles/20260829 codex usage` 整理为开发目录，保存源码、测试、文档、打包定义和启动器维护源；旧业务缓存、演示和临时产物按用途清理。
- 用户已复制到 `D:/AgentTools/state/codex-usage/启动用量统计.cmd` 的启动器，以**脚本自身所在目录**为运行根；报告、统计缓存及 GUI 设置均落在该根下。移动或复制脚本不依赖预设的 AgentTools 路径。
- CLI 给出三个默认方案，由用户选择；显式输出／缓存参数、query 的只读默认和独立安装能力保留。
- 系统 Python 的已安装包仍负责日常运行。原始 `.codex` 日志保持原位；本轮规划不改统计口径、价格、图表编号或日志解析含义。

本轮仅修订计划，不整理、删除或移动外部文件，不改运行启动器、系统安装和远端。前轮历史检索、原迁移依据与实现核查继续有效；新用户要求覆盖此前的输出位置选择。原迁移见 [计划](../../archive/20261113-agenttools-migration/plan.md) 与 [结果](../../archive/20261113-agenttools-migration/result.md)。

## 当前盘点与开发目录

源码及安装副本前轮核为 `edda407`／0.2.0。原目录中旧 SQLite 与两份 invalid 备份合计约 1.42 GB；`.task-tmp/` 约 224 MB；`codex_usage_report/` 32 文件约 207 MB。这些是 2026-11-15 观察，不把存在或大小当作可直接删除的充分依据。

建议保留现有平铺包结构、`docs/` 用户文档和 `dev_doc/` 开发说明，按数据用途整理；开发环境和临时目录可以按需再生成并忽略：

```text
原项目目录/
  codex_usage/                 Python 源码
  tests/                       合成测试
  docs/
    assets/                    固定的 README 展示媒体
    ...                        现有使用者文档
  dev_doc/                     现有开发文档
  scripts/
    启动用量统计.cmd           可复制启动器的唯一维护源
  .github/
  AGENTS.md
  CONTRIBUTING.md
  README.md
  pyproject.toml
  requirements.txt
  .gitignore、.gitattributes
```

`.git/` 保留；`.venv/` 可作为开发环境存在，`.task-tmp/` 可被现有测试按需创建，均不进入 Git。源码根和有效目录不为命名统一而全部改名；当前没有必须把包移入 `src/` 的需求。[PyPA](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)同时说明平铺与 src 两种布局及其导入差异；本次继续区分源码测试与源码外安装验收。

| 现有内容 | 规划处置 |
| --- | --- |
| `codex_usage/`、`tests/`、`.github/`、Git 历史 | 保留；同步必要路径引用 |
| `docs/`、`dev_doc/` | 保留现有读者分工和有效目录名；README 展示媒体统一归 `docs/assets/` |
| 根 `启动用量统计.cmd` | 维护源移至 `scripts/`，移除开发根的日常运行入口；部署同份脚本到用户选择的运行目录 |
| 根 SQLite、两份 `.invalid-*.bak` | 列为旧缓存删除项；实施前核当前有效缓存及调用方，无写入进程或消费者仍指向旧文件后删除 |
| 根 `codex_usage_settings.json` | 当前与 AgentTools 设置三项值一致；确认有效设置已在运行目录后清理旧副本 |
| `codex_usage_demo/`、各处 `__pycache__/` | 清理可再生成产物 |
| `.task-tmp/` | 清理旧内容，少量唯一补丁／必要原证先选留；现有五份测试仍使用该位置，不为改名改测试协议 |
| `.venv/` | 核其当前用途；不再使用的旧运行环境可删除，开发者按需建开发环境；不影响系统安装包 |
| `requirements.txt` | 保留。当前只有 `.[test]` 转接，不是重复依赖表；依赖唯一源仍为 pyproject，CI 正在使用此入口 |

**README 媒体须单独处理。** 旧报告目录有四个被 Git 跟踪的 GIF、MP4 和两张 PNG；两 PNG 与 MP4 的工作区内容已不同于已提交版本。规划将 HEAD 中的四件媒体按原字节移至 `docs/assets/`，只提交路径及链接变化；把当前完整真实报告移至运行区独立的旧报告目录，例如 `archive/20261115-project-report/`，避免覆盖现有 `reports/`。

两 PNG 禁止提交后续内容更新的约定随文件迁至新路径，现有较新 MP4 也不夹带提交。同步 README、AGENTS、CONTRIBUTING、开发文档及 `.gitignore`：README 改用固定展示媒体，不再要求文档图直接来自日常运行输出，也不新增生成预览脚本。旧报告目录移空且展示文件就位后，开发树中移除该运行产物目录。

## 启动器所在目录就是运行根

设脚本所在目录为 R。用户当前选择的 R 是 `D:/AgentTools/state/codex-usage`，脚本只从自身位置计算 R：

```text
R/
  启动用量统计.cmd
  codex_usage_settings.json     GUI 数据源、时区、归档选项
  cache/
    codex_usage_cache.sqlite3
    codex_usage_query_cache.sqlite3   仅实际增量查询使用时创建
  reports/                     图片、动画、CSV、JSON、gui_run.log
```

现有 `migration/` 及必要恢复原证按原职责保留。本次“cache 随脚本”覆盖用量工具自己的统计／查询缓存。

该 cmd 只启动 GUI 及其 report／cost 子进程，不执行 query。独立 CLI query 不继承已经结束的 `setlocal`；只有为 query 明确提供同一状态根或 `--cache-file` 时，才会使用 R 内的查询缓存。

优先复用已有路径解析，在脚本 `setlocal` 范围内明确设置：

```bat
set "CODEX_USAGE_STATE_DIR=%~dp0"
set "CODEX_USAGE_REPORT_DIR=%~dp0reports"
```

这两项覆盖保存的全局目录选择，也覆盖调用方遗留的同名环境变量；不把本次选择写回全局 `paths.json`。GUI 及统计子进程继承它们，脚本结束后调用方环境恢复。无需把 `CODEX_USAGE_CONFIG_FILE` 另绑一份目录注册表。

继续用所选系统解释器，从无关 cwd 加载安装包。分离前以同一 console Python 运行轻量 `gui --help`；用同目录 `pythonw.exe` 无等待启动 GUI，让双击产生的 cmd 退出。已成功 `pushd` 的成功／失败分支都须 `popd` 后 `exit /b`。缺解释器、pythonw、包或 Tk 时显示原错与操作指引，不自动安装或改用别的环境。

`start` 返回只证明派出进程；实际窗口验收确认 GUI 存活。沿用现有无控制台统计子进程，不另建握手、监护或重试协议。

移动整个 R 会带走已有设置、缓存和报告；只把 cmd 复制到一个空目录，会在那里使用新设置和新缓存，不自动寻找或搬运旧目录。两份脚本在不同目录运行时，各有自己的运行数据，仍使用同一个已安装包。部署脚本的版本源在 `scripts/`，更新时从该源替换运行副本。

## CLI 默认行为的三个方案

以下比较**未显式覆盖时**的默认行为；具体路径通过统一解析源产生，均不写死 `D:/AgentTools`。表中 cwd 指用户调用命令时的工作目录。

| 方案 | 报告默认位置 | 设置／统计缓存默认位置 | 适用与代价 |
| --- | --- | --- | --- |
| **A：报告随调用目录，状态按用户复用（推荐）** | `cwd/codex_usage_report/` | 平台用户工具目录，或用户已明确配置的状态根；缓存仍在 `cache/` | 适合一般报告 CLI；输出就在调用位置，跨目录统计可复用同一缓存；复制报告目录不包含缓存 |
| **B：项目局部** | `cwd/codex_usage_report/` | `cwd/.codex-usage/`，缓存在其中 `cache/` | 每个调用目录隔离设置和缓存；便于项目归档，代价是多份大缓存和首次解析 |
| **C：用户级应用目录** | 用户选定／平台默认运行根下 `reports/` | 同一运行根及 `cache/` | 接近当前个人仪表盘用法，CLI 从哪调用都更新同一处报告；输出不在当前工作目录，需要 `paths` 明示 |

三种方案都有常见实践可参照，并无适用于所有工具的唯一目录标准：报告工具 [coverage html](https://coverage.readthedocs.io/en/latest/commands/cmd_html.html) 默认写 `htmlcov` 并支持显式输出目录；[uv](https://docs.astral.sh/uv/concepts/cache/#cache-directory) 默认用平台用户缓存并允许覆盖；[pytest](https://docs.pytest.org/en/stable/how-to/cache.html#inspecting-cache-content)把缓存放项目的 `.pytest_cache`。A 是结合前两类职责作出的设计建议，B 参考项目局部工具，C 延续已安装个人应用的使用方式，不声称这些工具规定本项目必须如此。

所有方案共同保持：

- 输出／缓存的显式参数优先，其次环境变量、用户显式保存的目录选择，最后采用所选默认；相对参数相对调用方 cwd 解析，不从包的 `__file__` 找运行数据。
- `report` 生成报告；`cost`／`animate` 默认读取同一有效报告目录，并允许显式指定。直接 CLI 启动 GUI 时也使用同一解析合同；可复制 cmd 则始终显式选择脚本所在的 R，独立于通用 CLI 默认方案。
- `query` 默认 JSON 标准输出、只读扫描且不建缓存；`--incremental` 才采用方案对应的独立查询缓存，显式 `--cache-file` 仍优先。不因目录整改令只读查询开始写报告／缓存。
- `demo` 未指定输出时继续用有效状态根下的 `demo/`，CI 的无参数调用纳入路径回归。选择 B 时将新 `.codex-usage/` 加入本仓库忽略规则，防止设置、缓存和演示输出进入提交。
- `--help`、`paths` 只读；`paths` 显示实际解析位置，不仅显示理论默认值。沿用既有参数和环境变量，不为这三种比较同时实现三套模式。
- 本机当前保存有 AgentTools 的 `state_dir` 和 `report_dir`。选 A 时清除原保存的 `report_dir`，可保留用户已选定的 `state_dir` 以复用 AgentTools 缓存；选 B 时清除两项保存选择，才能采用 cwd 局部默认。只清相应配置键，不移动或删除 AgentTools 现有数据；环境变量仍按上述优先级生效。只改默认代码不足以证明本机行为已改变。

**建议选 A，CLI 选择仍待用户决定。** 启动器已明确使用 R 本地运行目录；CLI 无需再自动猜测源码目录、Git 根或启动器位置。选择后只实现一套默认规则，并同步路径帮助、配置与迁移说明。

## 实施顺序与验收

1. 在原项目核 Git／已提交媒体／工作区修改及当前解释器、有效缓存、在途进程；先登记本次路径映射。删除前验证所有递归目标的绝对路径在授权范围内，不停止用户在途统计。
2. 先分离固定 README 媒体、保留当前真实报告，再整理开发目录、启动器维护源和说明，最后删除确认失用的缓存／临时产物。逐项处理，不整树删除运行成果。
3. 修改可复制启动器并部署到用户现有运行根，用临时中文／空格目录中的两份脚本验证独立报告／设置／缓存及环境恢复。确认原 cmd 窗口退出而 GUI 存活，实际加载安装包。
4. 用户选定 CLI 方案后调整统一路径解析、相邻参数帮助／测试与本机目录配置。包内代码变化时构建并安装新版，再从源码外验收；仅启动器／文档变化不要求重装包。
5. 运行相应路径／CLI／GUI worker 回归，以合成日志实际完成报告和动画更新、取消及打开输出目录；验证 query 默认不建缓存、显式路径有效。清理目录后检查 README 图片、开发导航、CI 和打包内容。
6. 主 agent 统一复核差异，在原项目提交本次源码／文档／纯媒体移动，排除受保护 PNG 内容更新及已有 MP4 改动。记录实际删除、保留、移动与检查；远端发布另沿授权处理。

完成条件是开发目录用途清楚、固定展示媒体保持原字节、可复制启动器确实把运行数据写在自身目录下，以及选定 CLI 方案在安装包和本机配置中实际生效。当前只有计划和只读证据，尚未进行这些操作。
