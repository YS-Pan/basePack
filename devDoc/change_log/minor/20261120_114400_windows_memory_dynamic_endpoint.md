# Windows 项目库动态端口

0.18.8 为 Windows 用户任务增加可选的动态回环端口。项目配置保存 `:0`，客户端通过已登记任务取得本次实例的实际地址，HTTP、WebSocket 和原生传输复用同一实例。动态库支持常驻和空闲停机。`runtime export memory` 托管导出，`runtime import memory` 导入独立的新库并核对原 UUID 和 schema。

固定端口继续使用原接入。单库试点和同一候选包的真实验收见[托管进度](../../tasks/20261119-windows-user-runtime/progress.md#2026-11-20-动态端口产品接入与单库试点)。用户已取消协调者和读者的固定人数上限，实际工作量、宿主席位及每波的发布职责见[现行组织](../../tasks/20261115-real-use-rectification/maintenance-waves.md#组织与边界)。
