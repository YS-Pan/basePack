"""python jobs_run.py /absolute/project/.basepack/config.toml"""

import json
import sys

from basepack.project.config import load_project_config
from basepack.jobs import JobSpec, CondorClient

config = load_project_config(sys.argv[1])
result = CondorClient(config).run(JobSpec(
    executable=str(config.python),
    arguments=["-c", "print(sum(i*i for i in range(10000)))"],
    cwd=str(config.root), cpus=1, memory_mib=256, disk_mib=16,
    queue_timeout=120, run_timeout=30,
))
print(json.dumps(result, indent=2))
