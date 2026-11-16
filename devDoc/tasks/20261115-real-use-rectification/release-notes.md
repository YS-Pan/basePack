# basePack 0.16.0

This release addresses issues found while using basePack in real projects. It adds bounded maintenance handoffs and private classification for files kept in their original locations.

## Changes

- Publish large complete source snapshots as bounded messages within one native transaction. Original text, source versions, atomic rollback and native export/recovery remain intact. Invalid draft fields now identify their input location.
- Use `memory maintain --skip-codex-collection` to explicitly skip new chat collection while retaining registered sources, captured history and dependencies. Receipts report collection as not requested; chat freshness is not established. Known startup failures release only the current un-dispatched run when publication state is clear.
- Authors own finite related source groups and deliver fixed draft references. Role prompts use owned-branch events and recognize a later automatic final for the same references as the same completion.
- Use `memory stage` for a long run's fixed handoff. The same receipt, owner and control remain authoritative; the host ends the old group and actually spawns a new coordinator with clean history and a new identity. Finishing a stage does not imply completing the original receipt.
- Configure `[memory].private_scope` to classify selected files or directories in place. Root `private/` remains private. Frozen rules and versioned classification preserve historical provenance and reuse unchanged vectors; classification does not expand discovery or control Git publication.
- Clarify Condor execution-account, process-tree, application-parallelism and artifact/readback responsibilities. Correct the administrator Origin example to retain the endpoint's port.

## Upgrade

Requires Windows, Python 3.13+, and the facilities for the capabilities you enable. Finish existing maintenance and preserve the old client, configuration, credentials, database export and original/assets recovery set. Install the wheel normally and run `memory init` to refresh managed entry points. Keep the project UUID and existing credentials.

No database migration, unchanged-input vector rebuild or shared embedding-service upgrade is required from 0.15.0. Old frozen drafts without both privacy-rule fields can resume only under the known root-private contract with no additional private scope; changed rules require a new prepare/freeze cycle. Projects predating member-identity v2 still require the explicit offline migration; the unchanged migration-tools attachment is included.

See [project setup](https://github.com/YS-Pan/basePack/blob/v0.16.0/experiments/20261106-basepack/docs/setup-project.md), [memory](https://github.com/YS-Pan/basePack/blob/v0.16.0/experiments/20261106-basepack/docs/memory.md), and [resources](https://github.com/YS-Pan/basePack/blob/v0.16.0/experiments/20261106-basepack/docs/resources.md).

## Validation and limits

The source suite initially returned 694 passed, 3 failed and 1 skipped. The failing/skipped cases were covered by a 5-test normal-user rerun after correcting the Markdown-heading link validator; the final affected suite passed 62 tests, including new malformed-draft regressions. Large synthetic sources up to 8,943,755 bytes passed exact readback, rollback and native export/import checks.

Two real clean-context coordinator/reader stages published four sources under one receipt/run/control, verified exact source readback and query results, and completed parent stop/cancellation/release. A bounded Condor job verified the actual account, native worker threads and artifact hashes/readback. The local project client was upgraded while preserving configuration, mandatory content and database counts.

These checks do not establish token savings, complete chat freshness, external-project migration, or AEDT/GUI/license support. The known sandbox Codex SQLite access issue remains; the explicit collection choice does not repair its permissions. See the [delivery record](https://github.com/YS-Pan/basePack/blob/v0.16.0/devDoc/tasks/20261115-real-use-rectification/result.md) for evidence and scope. Local knowledge, credentials, models, caches and run artifacts are excluded from release packages.
