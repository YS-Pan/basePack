# 0.15.0规则修订、维护与发行结果

2026-11-15。规则修订、显式维护、最终包构建及本机客户端验证完成；[GitHub 0.15.0](https://github.com/YS-Pan/basePack/releases/tag/v0.15.0)已公开并设为Latest。

## 规则与实际修复

普通task不再因完成、终止或替代自动归档，也不例行扫描判断退役；用户明确要求时作为普通任务处理。ongoing只适用于正常业务中可顺手完成的简单有界整改，复杂调查、跨任务完成判断、批量迁移及公共合同/运行数据变更交普通任务。原默认168小时、发现到期整目录归档、不自动续期及保留未完状态的合同保留；没有撤销前次四任务归档。维护源为[文档约定](../../documentation.md)、[ongoing索引](../ongoing/README.md)，结构skill和框图同步。

实际freshness错误来自把自定义`codex-*.json`命令输出误认为原生采集回执。796416d按原生`codex-<32位小写hex>.json`命名选择；自定义文件不再遮住有效回执，坏的原生JSON仍抛原错。5项定向检查通过。本轮没有修复或掩盖受限shell的SQLite权限问题。

## 显式记忆维护

固定回执`b133446550804d6aa4cdb5f66321153c`的217/217来源完成（109新增、108既有变更），76个成功批次；4条原待决关系已处理。另4个关联来源用于必要共读和依据接续，不混入217计数。机械阶段51批、454复用块只是处理记录；完成依据是实际作者阅读/表示/有理由处置后程序接受，没有追加全库语义审计。维护中发现的错误作业类型摘要和关系端点已定点纠正。

JSON解析反馈`a27788a17c0041218d59a2f5e66c0e0c`已fixed：最终普通安装、59文件比对、独立回执样例及真实freshness调用通过。正常用户上下文读取当前聊天136parts成功、正确选中原生回执；返回明确不证明语义覆盖。`0fbd4bfef4254cb2969a91f69d22c7b4`仍pending：受限shell打开Codex状态SQLite的权限失败真实存在，正常入口成功不能证明沙箱权限已修复。

原捕获截断、不透明载荷及缺失结果按源保留；原采集96处gap和336项归属未明不是217来源中的失败数，也不证明完整历史覆盖。最后发行记录、freshness修复等截点后的新材料留后续维护。已stop自有control，确认全部维护agent结束、publications为空后release，最终owner=null；生产数据库和共享模型保持运行。

固定来源/版本/批次及收尾证据选留本机`artifacts/runs/20261115-release-0.15.0/maintenance-result.json`、`maintenance-receipts/`和`owner-final.json`，均不随Git发布。

## 发行包与本机验证

从提交`796416d9a1dd9a44813392b5f59cf4fab9957ee8`的隔离Git源码构建；实验工程tree为`7d43e51537b8bfff9594a255492a746db9070ba8`，后续根文档提交不改变该工程。59包文件匹配源码，67个wheel条目的RECORD、metadata、README和许可检查通过；干净环境普通安装、pip check及7项入口冒烟通过。额外验证了已装环境的custom回执排除和原生JSON错误保留。

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `basepack-0.15.0-py3-none-any.whl` | 141886 | `a6209ad8b71927439d38985a8abf007c593c9ac134e935eef30bb6ff286e113a` |
| `basepack-member-identity-v2-tools.zip` | 133156 | `abc377167b41c44f5bd0a772f09194abecff8687d14a746de24b564098d4d909` |
| `SHA256SUMS-0.15.0.txt` | 203 | `119bff2cca2b932ce7d4de989e80ab9e25159fce860d6f3ada824ad96a15c186` |

迁移ZIP沿0.14原字节。最终wheel已替换本项目稳定客户端，59安装文件逐字节匹配，pip check及真实freshness通过。共享服务沿此前0.15安装，embedding代码未再改变，本轮未重启服务或迁库。已有654项功能检查、GPU/HTTP/旧索引与数值边界见[实施交付](../../archive/20261115-runtime-and-maintenance/result.md)；本次按freshness改动运行5项定向检查和包装/安装验证，不重复全套，也未量化长期token收益或显存百分位。

## GitHub发行

本地21项提交正常快进推送至[YS-Pan/basePack](https://github.com/YS-Pan/basePack)。[v0.15.0](https://github.com/YS-Pan/basePack/releases/tag/v0.15.0)于北京时间2026-11-15 **16:49:24**公开，非草稿、非prerelease并设Latest；Release ID为445921314，标签指向`70be61b997977ad40f9e338e81d37bea21df986f`。该提交包含规则、freshness修复和维护结果，实验工程tree与构建源796416d完全相同；main随后只补发行记录和根README链接，不改发行包。

草稿阶段已核目标提交、[英文说明](release-notes.md)、3附件大小和GitHub digest，并下载逐字节比对；公开后再次重下，全部SHA256及字节仍相同，远端标签指向上述提交、Latest API返回本次Release。选留证据为本机`artifacts/runs/20261115-release-0.15.0/github-draft.json`及`github-published.json`。公开范围不含项目记忆、数据库、配置、凭据、模型及本机运行原证。本任务按新约定保留在tasks，不自动归档。
