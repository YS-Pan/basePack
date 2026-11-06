# 2026-11-07 · 明确采用 let it crash

按用户进一步澄清，将 [AGENTS.md](../../../AGENTS.md) 的简洁约定改为明确避免防御式编程：内部遵循契约，非预期错误直接抛出并保留原始信息，仅捕获有明确处理办法的异常，避免用兜底和重复校验审阅掩盖失败。既有模块职责、状态单一维护源和真实缺陷回归约定保留。

联网核实 [Joe Armstrong 论文 §4.4](https://erlang.org/download/armstrong_thesis_2003.pdf) 与 [Elixir 官方说明](https://elixir.hexdocs.pm/try-catch-and-rescue.html#fail-fast-let-it-crash)：对有已知处理办法的情况采取明确动作，对非预期错误让其失败；此处采用该编程原则，不因此引入重启或监督框架。

检查文档差异、本地链接、UTF-8 与纲领 SHA-256；未修改纲领。
