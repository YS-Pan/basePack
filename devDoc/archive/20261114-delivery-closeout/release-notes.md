# v0.13.0.dev1

Development release for Windows and Python 3.13+. Source, ordinary-wheel installation, this project's UUID migration and the existing shared CUDA service have been checked; this is not a clean-machine or long-term quality claim.

- Program-assigned member UUIDs, scoped draft references and immutable publication batches. Identical frozen retries are idempotent; conflicting updates, duplicate writes and old protocols fail explicitly.
- Read-only Codex freshness inventories and targeted body comparison. Retrieval workers supplement published knowledge with relevant current chats and report capture/semantic gaps.
- A small independent `basepack-setup` skill routes installation and upgrade work to the existing guides.
- Native Condor job limits and cleanup, with JSON argv preservation and uncertain-submit recovery. Observation expiry leaves jobs running; cancellation requests and terminal states are separate.
- Embedding diagnostics return HTTP 422 with original request indices and token counts, preserving model identity and vectors. Update the service package to enable them.

**Breaking upgrade:** existing memory projects must stop writes, preserve their recovery set, migrate member identities and structural references in isolated stores, validate, then switch database and client together. `memory init` does not migrate old data. Preserve the old wheel and never replay old-ID batches or pending delivery manifests into the new database. The separate recovery utility targets the eleven-table knowledge/access schema used by 0.12; earlier schemas require their own preparation. See [upgrade instructions](../../../experiments/20261106-basepack/docs/setup-project.md#版本升级) and [verified delivery](result.md).

Validation: 618 tests passed without skips; ordinary-wheel create/read/search/update/retry/conflict flow; full migration equivalence plus historical text/image/graph/delivery reads; two real CPU Condor jobs; live text/image and 422 service checks. Model, embedding identity, project UUID and credentials were retained. Other projects and three independent tools were not migrated by this release.

Retrieval invocation still depends on the host agent following its instructions. Capture, semantic acceptance and vector coverage are separate; unknown ranges remain explicit.

Attachments: `basepack-0.13.0.dev1-py3-none-any.whl`, `basepack-member-identity-v2-tools.zip`, `SHA256SUMS-0.13.0.dev1.txt`.
