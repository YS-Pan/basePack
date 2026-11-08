# 分离 embedding 职责与身份

R8.2 将启动者、固定模型和进程所有权改为 supervisor、Qwen3VLEmbedder、WorkerProcessOwner，并分开 transport、registry、identity 和 admin。EmbeddingClient 明确接收 MachineConfig；机器管理命令为 `embedding --machine-config <file> serve|status|stop`，无需项目配置。

协议版本、embedding_identity 与 deployment_fingerprint 各有单一合同。语义标识包含模型/预处理/pooling，运行设置和路径归部署指纹；启动进程固定身份，管理员可比较磁盘目标并用旧 marker 停止旧实例。物理 broker 登记路径保留。

源码全套 51 passed；独立 embedding 22 项覆盖单 worker、取消/截止、冷启动取消、空闲释放、旧 marker、协议与 Windows 崩溃回收，机器 CLI 轻量检查通过。未改稳定安装或真实共享服务，部署留待 R8.4。
