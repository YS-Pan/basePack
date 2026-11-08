"""python resources_run.py /absolute/path/to/project/basepack.toml"""

import json
import sys

from basepack.config import load_config
from basepack.resources import JobSpec, ResourceClient

config = load_config(sys.argv[1])
result = ResourceClient(config).run(JobSpec(
    executable=str(config.python),
    arguments=["-c", "print(sum(i*i for i in range(10000)))"],
    cwd=str(config.root), cpus=1, memory_mib=256, disk_mib=16,
    queue_timeout=120, run_timeout=30,
))
print(json.dumps(result, indent=2))
