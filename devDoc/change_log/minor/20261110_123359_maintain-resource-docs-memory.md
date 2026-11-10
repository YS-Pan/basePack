# 维护资源认证边界文档与项目记忆

现行文档明确：受限沙箱容量查询成功而队列仍有 NTSSPI/AUTHENTICATE:1005，正常用户上下文可查询且已完成 CPU/GPU 实测；正常用户成功不表示沙箱限制已消除。管理员说明补齐分别核查、实时 startd 地址、设备 UUID 和实际进程/资源回收方法，资源模块统一指向流程与本机结果。

本项目记忆的原3来源保持，source_scope 增加环境、资源模块和管理员说明至6源；项目 instructions 增加资源操作的按需入口。本次一次 apply 新增34表示、3节点、5语义边并实际编码，原3条 mandatory 不变。环境与管理员说明仅覆盖本次资源主题，其余章节显式保留 coverage_gaps。

已复现并保存双上下文只读认证对照；两条默认 hybrid 检索均召回对应原文，read/neighbors 验证内容与条件，六源 deep changes 为空，pending及待编码均为0。文档新链接、锚点、UTF-8、scope及差异检查通过。未改产品代码、项目纲领、机器认证配置或共享服务。

维护原证见 `artifacts/runs/20261110-resource-docs-memory/verification.json`，认证对照见 `artifacts/runs/20261110-condor-auth-context/`；本地记忆批次、配置和数据库留在 Git 忽略的 `.basepack/`。
