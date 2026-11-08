# basePack

basePack 为多个项目提供共享本地 embedding 与 HTCondor 重任务入口。项目数据留在各自项目，模型与机器资源显式共用。当前正在实施资源工具；记忆检索、建图和数据库尚未交付。

需要 Python 3.13。开发时对现有系统 Python 执行：

```powershell
python -m pip install -e .
```

稳定部署安装构建好的 wheel，不依赖源码仓库。项目使用同一套配置：[项目接入](docs/setup-project.md)。开发约定见 [AGENTS.md](AGENTS.md)。
