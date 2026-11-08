# 将当前实现归入完整实验工程

将 basepack 的源码、依赖声明、测试、产品文档、示例、resources skill 和交付包成组迁入 `experiments/20261106-basepack/`，作为唯一 active 路线，为 memsys 等后续大改准备独立工程边界。根保留统一 devDoc 与两项通用技能，README/AGENTS 指向当前路线；现行部署合同归 system。实际映射与验收见 [迁移结果](../../archive/20261109-project-layout/result.md)。

同步构建/安装/测试命令、文档引用、忽略规则和资源 skill 发现联接，选留原证统一归 artifacts/runs。990 份原证及旧 wheel 的哈希保持，44 份源码/测试/样例字节不变。pytest 因实测相对缓存路径缺陷改为禁用 cacheprovider，验证使用直接 Python 避开 Windows venv 启动器的 PID 差异，原失败日志保留。

实际检查：源码和隔离新 wheel 各 92 项回归通过；源码外初始化、CLI、深层中文配置、模板/许可及轻量命令通过；根/实验目录技能发现正确。机器和 Condor 配置、共享安装与服务未改动。文档链接、原文哈希、Git 边界和差异检查通过。本轮未执行 R9 或记忆功能、未推送远端。
