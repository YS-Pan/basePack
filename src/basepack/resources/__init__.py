"""Local HTCondor jobs with explicit resource budgets."""

from .client import JobSpec, ResourceClient, budget_config

__all__ = ["JobSpec", "ResourceClient", "budget_config"]
