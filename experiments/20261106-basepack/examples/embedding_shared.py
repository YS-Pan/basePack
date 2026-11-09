"""Two projects reuse one model; the Windows service must already be running."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math

from basepack.project.config import load_project_config
from basepack.embedding import EmbeddingClient

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("project_a_config")
parser.add_argument("project_b_config")
args = parser.parse_args()
a = EmbeddingClient(load_project_config(args.project_a_config).machine)
b = EmbeddingClient(load_project_config(args.project_b_config).machine)
with ThreadPoolExecutor() as pool:
    batch = pool.submit(a.embed, ["document one", "document two"])
    query = pool.submit(b.embed, ["find a document"])
    results = [batch.result(), query.result()]
assert results[0]["pid"] == results[1]["pid"]
print(json.dumps([{"pid": value["pid"], "embedding_identity": value["embedding_identity"],
    "dimensions": [len(vector) for vector in value["vectors"]],
    "norms": [math.sqrt(sum(x*x for x in vector)) for vector in value["vectors"]]}
    for value in results], indent=2))
