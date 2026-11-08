# basePack 项目入口

本项目配置为 `$config`，运行 Python 为 `$python`。从项目根运行：

```powershell
& '$python' -m basepack --config '$config' config show
```

在其它工作目录调用时，显式传该配置的绝对路径；不搜索父目录。首次接入或设施变化时运行 `doctor`，平常直接执行所需动作。资源调用按安装包的 `embed` 与 `resources` 帮助使用；共享模型由机器管理员启动。

项目配置、知识与工具产物保留在本项目 `.basepack/`，业务原件和显式导出按业务路径保存。新检出后通过 `init` 重建本机配置与本入口，不复制其它项目的知识或任务状态。
