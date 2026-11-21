# 正式切换共享 embedding 并隐藏控制台

共享 embedding 接到 Windows 普通用户任务，继续使用同一 CUDA 模型和回环端口 `8765`。任务及服务子进程使用 `pythonw.exe`，推理 worker 的输出写入任务日志。

实际通过 Auto Review 冷启动。状态、进程树、日志和四个旧版项目的 brief 与向量检索均复验通过。46 项运行时与客户端回归通过。[验收和回退记录](../../tasks/20261119-windows-user-runtime/progress.md#正式共享-embedding-切换)
