# basePack

basePack 让多个项目共用一套本地多模态 embedding，并通过 HTCondor 排队执行 CPU/GPU 重任务。项目输入、结果与作业记录留在各自项目；共享服务只加载一份模型。

0.3.0 面向单机 Windows、单张 NVIDIA GPU，使用已有 Python 3.13、Qwen3-VL-Embedding-2B 权重和 HTCondor。普通作业使用官方 GPU 申请字段，由 Condor 站点策略预订显存并安排同卡共享；embedding 独立在背景运行。记忆检索、建图和数据库由独立任务建设。

稳定使用安装普通 wheel；在可供服务和 Condor 执行账户读取的系统 Python 中安装：

```powershell
python -m pip install '<basepack-wheel>'
python -m basepack init --project-root '<project>' --machine-config '<absolute-machine-config>'
python -m basepack --config '<absolute-project>/basepack.toml' config show
```

机器配置、Condor 站点策略和独立 embedding broker 由管理员首次设置，项目无需复制模型或编写 Condor submit 文件。原生 Condor 用户只需填写 `request_gpus = 1` 和 `gpus_minimum_memory = <峰值> MB`，无需安装 basePack。[项目接入](docs/setup-project.md) 说明安装与换路径，[资源使用](docs/resources.md) 给出图文 embedding、一次 run 及长任务接续，[管理员说明](docs/administrator.md) 负责站点策略与服务生命周期。agent 可使用 [resources skill](skills/resources/SKILL.md)。

本机开发用 `python -m pip install -e <repo>`；普通模块修改由新进程加载。稳定部署与交付验收使用普通 wheel，切换前先排空并停止受影响共享服务。开发入口与实际验收状态见 [AGENTS.md](AGENTS.md) 和 [资源进度](devDoc/tasks/20261107-resource-coordination/progress.md)。
