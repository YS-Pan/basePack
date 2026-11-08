"""Local HTCondor jobs with explicit resource budgets."""

from .client import JobSpec, ResourceClient

__all__ = ["JobSpec", "ResourceClient"]
