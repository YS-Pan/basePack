# basePack 0.14.0

basePack is under development. This release targets Windows and Python 3.13+; compatibility and verification limits remain explicit despite the simpler numeric version.

- Keep confidential development originals and analysis in an optional project-root `private/` with its own local Git repository, excluded from public Git and release packages. Public documentation stays self-contained, with optional private references.
- Discover that private repository's tracked and nonignored files alongside public project sources, using the same project UUID and memory database. Explicit discovery scopes keep their existing boundaries.
- Carry a `private` boolean through source snapshots, knowledge and version-pinned evidence. Mixed public/private knowledge is marked private; retrieval and handoffs retain the observed marker. Missing markers on old records remain unconfirmed.
- Extend the independent `file-structure` skill with the private-context pattern and its backup, publication and retirement boundaries.

**Upgrading:** preserve the project's full recovery set and finish active writes before upgrading. Projects already using member-identity version 2 retain their UUIDs, knowledge identities and vectors. Refresh generated entry points with `memory init`; it does not migrate an older database. Pre-0.13 projects need the separate offline member-identity migration, with isolated validation before switching database and client together. The unchanged migration-tools attachment targets the documented eleven-table knowledge/access schema; older schemas need their own preparation. See the [upgrade instructions](https://github.com/YS-Pan/basePack/blob/v0.14.0/experiments/20261106-basepack/docs/setup-project.md#版本升级) and [configuration maintenance](https://github.com/YS-Pan/basePack/blob/v0.14.0/experiments/20261106-basepack/docs/project-config-maintenance.md#按变化边界准备恢复集合).

Private markers do not provide access control or sanitize an export. Full recovery backups still contain public and private content. Existing-record marking uses confirmed mappings and fixed-version evidence; unknown historical records are not declared public. A public-memory export tool is not included. See the [sharing boundary](https://github.com/YS-Pan/basePack/blob/v0.14.0/experiments/20261106-basepack/docs/memory.md#私有资料与分享边界).

Feature validation covered 634 tests across the original run and its corrected-environment checks, plus a 146-test final prompt check. Ordinary-wheel validation exercised private Git discovery, mixed-provenance marking, retrieval/history and retained snapshots; an isolated restore preserved the existing knowledge and vectors. This release's packaging checks validate the current wheel and a clean normal installation. Clean-machine facility deployment and long-term quality/cost benefits remain for real-use feedback. See the [delivery record](https://github.com/YS-Pan/basePack/blob/v0.14.0/devDoc/tasks/20261114-next-maintenance/result.md).

Attachments: `basepack-0.14.0-py3-none-any.whl`, `basepack-member-identity-v2-tools.zip`, `SHA256SUMS-0.14.0.txt`.
