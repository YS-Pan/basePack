"""Standard HTCondor submission and job lifecycle observation."""

from .client import CondorClient
from .submit import JobSpec

__all__ = ["JobSpec", "CondorClient"]
