# basePack maintenance trial

This trial is complete. Its verified changes have been merged into the sole active route, [20261106-basepack](../20261106-basepack/README.md), targeting 0.10.0.dev1. This directory retains the trial entry, rather than a second maintained implementation.

The independent candidate started from 0.9.1 at commit `490b1c219ef92b625dd3075a0516ce6c761c5f80`. It covered owner-based maintenance, direct agent entry instructions, atomic SQL message batching, parent dependencies, persistent use feedback, read dispositions and gradual refinement.

See the root [implementation result](../../devDoc/tasks/20261106-memory-system/maintenance-implementation-result.md) for actual tests, installation, memory maintenance and limits, and the [plan](../../devDoc/tasks/20261106-memory-system/automatic-maintenance-plan.md) for the accepted contracts. The tested source snapshot, consolidation hashes and selected evidence remain in [run artifacts](../../artifacts/runs/20261111-maintenance-implementation/).

The small agent comparison did not demonstrate lower total cost. Ordinary maintenance completes after authoring and program publication; audits require explicit user intent.
