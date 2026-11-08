# basePack

basePack 让多个项目共用一套本地多模态 embedding，并通过 HTCondor 排队执行 CPU/GPU 重任务。项目配置、工具产物和作业记录集中在各自的 `.basepack/`；共享服务只加载一份模型。

0.4.0 面向单机 Windows、单张 NVIDIA GPU，复用 Python 3.13、Qwen3-VL-Embedding-2B 权重和 HTCondor。普通作业使用官方 GPU 申请字段，容量与队列由 Condor 管理；embedding 独立运行。记忆检索、建图和数据库由独立任务建设。

在可供服务和 Condor 执行账户读取的 Python 中普通安装 wheel，然后接入项目：

```powershell
python -m pip install '<basepack-wheel>'
python -m basepack init --project-root '<project>' --machine-config '<absolute-machine-config>'
python -m basepack --config '<absolute-project>/.basepack/config.toml' config show
python -m basepack --config '<absolute-project>/.basepack/config.toml' jobs run --spec '<job.json>'
```

管理员准备机器配置和 Condor 策略，并在作业树外运行 `embedding --machine-config <file> serve`。项目无需复制模型或编写 Condor submit 文件。原生 Condor 用户继续使用 `request_gpus = 1` 和 `gpus_minimum_memory = <峰值> MB`，无需安装 basePack。

[项目接入](docs/setup-project.md) 说明配置、旧版本迁移与换路径；[资源使用](docs/resources.md) 给出图文 embedding、jobs 和 Python API；[管理员说明](docs/administrator.md) 负责安装、策略与服务生命周期。agent 可使用 [resources skill](skills/resources/SKILL.md)。0.3.0 项目须排空旧作业、停止旧服务并显式迁移后使用新接口。

开发可用 `python -m pip install -e <repo>`，稳定部署使用普通 wheel；同一解释器保留一种有效安装。本机实际安装和验收状态见 [资源进度](devDoc/tasks/20261107-resource-coordination/progress.md)，开发入口见 [AGENTS.md](AGENTS.md)。
