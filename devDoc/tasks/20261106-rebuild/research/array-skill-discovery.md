# array reconstruct 的 skill 发现入口调查

调查日期：2026-11-10（北京时间）。调查时状态：根因已定位，接入修复待实施。该次只调查并记录，未修改 array reconstruct、客户端安装或产品实现；后续实际修复与宿主发现的现行状态见末节。

## 结论

用户指出的问题成立：`D:/project/20261109 array reconstruct` 复制了两项 skill 的维护原件，却没有建立项目级自动发现入口 `.agents/skills/`（复数）。其 `AGENTS.md` 第 6 行直接引用 `skills/`，可引导 agent 显式读取，但不能据此认定宿主已经发现和注册了这些 skill。

直接遗漏发生在迁移交付的发现入口与验收；basePack 的配套缺口是程序接入与独立 skill 安装分开，`init` 和 `doctor` 都不覆盖后者。旧客户端与当前源码均如此，单纯升级客户端不会补齐入口。这不影响已经单独验收的项目记忆功能。

随包 memory skill 由 `memory guide` 定位，并经 `.basepack/instructions.md` 直接引用；这是已有的另一条流程入口，不能与两项通用 skill 的宿主发现混为一谈。

[OpenAI 官方说明](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)规定项目技能从 `.agents/skills` 发现，并支持链接目录。普通 `skills/` 是本仓库的维护源路径；本仓库依靠另外建立的 junction 将其接入发现目录。这些本机链接被 Git 忽略，复制维护源不会携带它们。

## 版本与时间边界

| 对象 | 实际证据 | 本次结论的适用范围 |
| --- | --- | --- |
| array reconstruct 的迁移 | 聊天 `01a1c393-17db-7f73-a77f-7696d1802836`；初始提交 `a6fff2a`，2026-11-10 12:22:19 +08:00 | 使用普通安装的 basepack 0.6.2；两项技能共 6 个文件复制到 `skills/` |
| 外部项目调查快照 | HEAD `576946a7f6fc1daee928139f65a69bdf2a63f2c8`；本地接入与验收记录 | `.agents`、`.agents/skills` 均不存在；6 个技能文件的 SHA256 与本仓库当前维护源逐个相同 |
| 共享 embedding | 外部接入记录报告服务 0.5.0 | 是模型服务版本，与项目 skill 安装无关 |
| 已安装客户端 | 稳定 Python 的 site-packages，0.6.2 | 隔离运行 `init` 与显式 `doctor core` |
| 当前源码 | 核查基线 HEAD `f8bb5b255c559cf010245daa1e9a09ac79373160` 加并行任务的未提交修改；导入源码的模块版本为 0.6.4 | 隔离执行相同操作；工作区 README 已写 0.7.0 开发版，不能据此认定已有 0.7.0 安装交付 |

根 README 面向外部项目的 `.agents/skills` 完整目录复制步骤，首次加入于 `cf96ec00ef95379c0ea47440dc59b589dab89006`，时间为 2026-11-10 13:17:24 +08:00，晚于此次迁移。更早的环境说明已有本仓库 junction 的手工建立方法。因此不能用后加的 README 步骤倒推迁移当时违反了既有外部安装流程；能确认的是整体技能接入未完成，也未验收发现行为。

## 实际检查

- 只读核对外部目录、AGENTS 指针、迁移结果、接入记录、6 个文件哈希及所给聊天。迁移记录验收了文件保真、文档链接、记忆闭环，没有提供宿主 skill 发现验收；未完整审计全部嵌套 agent 聊天。
- 阅读当前 [init](../../../../experiments/20261106-basepack/src/basepack/project/init.py) 与 [doctor](../../../../experiments/20261106-basepack/src/basepack/project/doctor.py)。`init` 只生成配置、instructions、AGENTS 指针与 Git 忽略项；doctor 的 core 检查覆盖 Python、项目根、包和模板，没有技能检查。
- 在两个全新临时项目分别实际调用已安装 0.6.2 与当前源码的 `init_project`，再显式运行 `doctor(..., 'core')`。两者都成功，只生成 `.basepack/config.toml`、`.basepack/instructions.md`、`.gitignore`、`AGENTS.md`；均无 `.agents` 或 `skills`。源码导入位置单独核对，doctor 返回的安装模式不能作为普通安装证明。
- 静态查看保留的 0.6.0–0.6.4 wheel，技能文件均仅含 `memory/SKILL.md`；通用技能未随 wheel 安装。0.6.1–0.6.4 的 `project/init.py` 与已安装 0.6.2、当前源码相同。

选留原证在根 `artifacts/runs/20261110-skill-discovery/`：`target-evidence.json` 保存外部目录和哈希，`receipt.json` 保存两次隔离结果，`package-contract.json` 保存 wheel 和历史版本核对，`reproduce.py` 与 `capture.py` 保存检查脚本，`thread-evidence.json` 保存主聊天中的相关命令摘录。脚本按原执行条件使用项目根 `tmp/skill-discovery-investigation/`；重新执行需使用全新临时项目名。未运行外部项目的宿主 `skills/list`，不宣称已完成宿主端发现验收。

## 后续修复建议

先为 array reconstruct 的两项已有技能补齐发现入口：可将项目内 `.agents/skills/<name>` 链接到本项目已有的 `skills/<name>`，保持一份维护源；在该项目的新聊天或宿主技能列表核对名称、项目作用域和可读取路径。重新检出也需要重建链接。另一种交付方式是直接将完整目录保存在可提交的 `.agents/skills/` 并同步 AGENTS 引用，避免同时维护两份副本。

basePack 应将“选择并安装所需独立 skills → 核对宿主发现结果”纳入完整项目接入的说明与验收，明确 `init` 的实际覆盖范围。若产品目标改为一个命令完成全部接入，还需决定通用技能如何随安装产物取得；仅修改 init 创建空目录，或在 core doctor 中无条件要求全部技能，不能完成该目标。

此处为调查建议，尚未修改接入行为，也未执行外部项目修复。当前 [README 的独立 skills 步骤](../../../../README.md#independent-skills)已可供新项目手工安装，但现有项目仍需补做。

## 可复制 Issue 草稿

```text
标题：项目接入完成后可能只有 skills 原件而缺少宿主发现入口
版本与环境：Windows；basepack 0.6.2 普通安装；当前工作区源码亦复现
预期与实际：完整基础设施接入后所选技能应被宿主发现；迁移仅复制到 skills/，无 .agents/skills
最小复现：全新项目执行 init 与 doctor --facility core，均成功，但不生成或检查技能发现入口；另将完整 skill 复制到 skills/ 也不会建立该入口
本地记录：devDoc/tasks/20261106-rebuild/research/array-skill-discovery.md
处理状态与验证：根因已定位，未修复；已核文件哈希、历史版本和两条隔离初始化流程，宿主发现验收待修复后执行
```

草稿保存在本仓库，未向 GitHub 提交。外部项目本身的后续记录应沿其现有约定维护。

## 2026-11-10 接入修复接续

以上保留调查当时的版本、缺口与建议。本轮按 [接入简化计划 A](../../../archive/20261110-onboarding-simplification/plan.md#a补齐技能接入闭环) 完成两项既有技能的发现入口修复，未新增 engineering-judgment，也未运行技能行为或效果测试。

外部项目 `D:/project/20261109 array reconstruct` 的 `.agents/skills/agent-team` 与 `.agents/skills/file-structure` 均为指向本项目 `skills/` 原件的 junction；相对引用随完整原件可达。该项目以 `main` 提交 `931634e` 保存两条精准忽略项及 `devDoc/system/basepack.md` 本机重建说明，提交后工作区干净。

随后实际调用受支持的 Codex App Server `skills/list`，参数 `cwds=[外部项目根]`、`forceReload=true`。返回两项名称、`scope=repo`、解析到该项目原件的 SKILL.md 路径，且 `errors=[]`；本轮已验收宿主实际发现。原证为根 `artifacts/runs/20261110-onboarding-simplification/docs-array-skills-list.json`，具体文档交付与检查见 [本轮结果](../../../archive/20261110-onboarding-simplification/documentation-result.md)。
