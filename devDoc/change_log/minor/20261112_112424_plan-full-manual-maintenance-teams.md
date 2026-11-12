# 将手动维护数量算法改为只规划满队

2026-11-12（北京时间）。用户要求手动维护使用两个满队，不为余量再开只有一个reader的小队。

修订[维护计划](../../tasks/20261106-memory-system/task-duration-and-worker-naming-plan.md)：手动M≥5时T=min(10,floor(M/5))，规划T名coord、4T名reader，余量留空；M=1至4时保留单coord兼reader，自动算法保持。同步组织图、算例、验收与进度，评估继续引用单一合同。仅改文档，未实施程序；离线核对人数和边界、检查UTF-8／链接／锚点及Git差异。
