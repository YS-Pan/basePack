"""Keep application argv intact across HTCondor's Windows argument conversion."""

import json
from pathlib import Path
import subprocess
import sys


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["spec"]
    raise SystemExit(subprocess.call([spec["executable"], *spec["arguments"]]))


if __name__ == "__main__":
    main()
