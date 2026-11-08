# 项目接入

机器管理员先选择 Python，安装 basePack wheel，建立机器配置。模板可从已安装包读取：

```powershell
python -c "from basepack.setup import template; print(template('machine.toml'))"
```

填写模型路径、现有 HTCondor 的 bin_dir/config_file 与实测预算。相对机器路径以机器配置所在目录为基准。开发机用 `python -m pip install -e <repo>`，普通模块修改由新进程加载；稳定部署用 `python -m pip install <wheel>`。切换安装模式后，排空工作并重启受影响服务。

每个项目执行一次：

```powershell
python -m basepack init --project-root '<project>' --machine-config '<absolute-machine-config>'
python -m basepack --config '<absolute-project>/basepack.toml' config show
python -m basepack --config '<absolute-project>/basepack.toml' doctor --facility core
```

init 从安装包模板生成配置，写入当前 Python 路径，合并 AGENTS 的工具入口与 Git 忽略项。现有配置存在时直接报错。配置放子目录可传 `--config-name config/basepack.toml`。不向父目录寻找配置，调用时显式传实际配置绝对路径。

项目配置只绑定 Python 与机器配置，数据相对 project.root 定位；移动项目不改变机器绑定。换机器时更新这两个绝对路径。`.basepack/` 和实际配置不进 Git，AGENTS 可提交。`config show` 返回实际加载位置及安装模式，供诊断，不再保存为另一份运行配置。

`doctor --facility embedding` 或 `condor` 只读检查对应设施；它们不代替真实推理、作业产物和并行验收。普通业务任务不必全部交给协调器，显存/内存等声明由调用者按实际负载粗估。
