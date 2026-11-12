"""Thin LitServe adapter; Shawl owns the Windows service process tree."""

from importlib.metadata import version
from urllib.parse import urlsplit

from fastapi import HTTPException
from litserve import LitAPI, LitServer

from .identity import DTYPE, embedding_identity
from .qwen3_vl import EmbeddingInputError, Qwen3VLEmbedder, resolve_device


class EmbeddingAPI(LitAPI):
    def __init__(self, options):
        super().__init__(max_batch_size=1)
        self.options = options

    def setup(self, device):
        self.model = Qwen3VLEmbedder(self.options | {"device": device})

    def decode_request(self, request):
        return request["inputs"]

    def predict(self, inputs):
        try:
            return self.model.embed(inputs)
        except EmbeddingInputError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error


def serve(machine):
    configured = machine.raw["embedding"]
    options = configured | {"model_root": str(machine.path_value("embedding", "model_root"))}
    device = resolve_device(configured["device"])
    options["device"] = str(device)
    endpoint = urlsplit(configured["endpoint"])
    server = LitServer(
        EmbeddingAPI(options), accelerator=device.type,
        devices=[device.index if device.index is not None else 0] if device.type == "cuda" else 1,
        workers_per_device=1, timeout=configured["queue_timeout"], restart_workers=True,
        model_metadata={"embedding_identity": embedding_identity(options), "device": str(device), "dtype": DTYPE,
                        "basepack": version("basepack"), "litserve": version("litserve"),
                        "sentence_transformers": version("sentence-transformers")},
    )
    server.run(host=endpoint.hostname, port=endpoint.port, num_api_servers=1, generate_client_file=False)
