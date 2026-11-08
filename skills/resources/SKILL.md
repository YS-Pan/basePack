---
name: resources
description: Use basePack's shared text/image embedding and HTCondor heavy-job tools in a configured project. Apply when calling these tools, estimating their resource requests, or continuing an existing basePack job.
---

# Resources

Read the project's indicated `basepack.toml`. Invoke its `runtime.python` with `-m basepack --config <absolute-config>`; the machine configuration supplies model, broker and Condor paths. On first setup or an environment change, use `config show` and the relevant `doctor --facility`; ordinary calls go straight to the action.

- **Embedding:** `embed --text <text>` or `embed --image <absolute-image> --caption <text>`. Use `--inputs <UTF-8-JSON-array>` for batches and `--output <project-file>` to keep vectors out of the conversation. Query and bulk work share the model. A missing broker requires the machine-level launcher outside every Condor job tree; clients only connect.
- **Heavy work:** write a UTF-8 JobSpec with an absolute `executable`, an `arguments` array, project-relative `cwd`, `cpus`, `memory_mib`, `disk_mib`, and bounded `queue_timeout`/`run_timeout`. For GPU work add `gpu_memory_mib`, including context, caches and workspace. Use `resources run --spec <file>` for one submit-and-wait call.
- **Long work:** `resources submit --spec <file>`, then `resources wait <cluster.proc> --timeout <seconds>`. Observation expiry leaves the job running. Use `resources status <cluster.proc> --analyze` for queue/hold diagnostics and `resources cancel <cluster.proc>` to cancel that job.

Keep project inputs and outputs in the project. CPU/RAM/GPU values are cooperative estimates; cap application threads and framework allocations accordingly. Preserve Condor's `CUDA_VISIBLE_DEVICES`. A job that exceeds machine capacity is rejected; one that fits but lacks current capacity queues. The shared embedding reserve remains available even before model loading.

Check application exit code and meaningful output, and report `cleanup_confirmed` separately from timeout. Preserve original errors and log locations. An embedding deadline or client close only affects its own requests; `embedding stop` is a separate machine administration action.

Use [resource examples](../../docs/resources.md) for input limits, transfers and Python calls; [project setup](../../docs/setup-project.md) for connection or relocation; [administrator guidance](../../docs/administrator.md) for broker ownership, budget publication and package upgrades. Package help is available without the source repository.
