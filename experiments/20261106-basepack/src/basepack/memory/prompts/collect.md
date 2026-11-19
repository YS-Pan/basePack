Collect Codex chat originals for the assigned project. This is an independent operation before maintenance ownership.

1. Resolve the assigned parent chat's Codex project ID and all registered local project roots from the host. Verify its ID against the project's configured binding. Save a fresh UTF-8 JSON object at `$registry` with `project_id`, `other_project_roots` (all other registered local project roots), and `registry_complete: true`. If the binding or complete registry is unavailable, report the coverage gap and leave collection pending.
2. Use the following command in `$root`.

   ```text
   $command
   ```

   When a Windows Codex sandbox restricts the Codex user state directory and the current host session routes shell escalation to Auto-review, submit this single command for execution outside the sandbox as the signed-in Windows user. Use the shell tool's escalation option (`sandbox_permissions="require_escalated"` where available) and this reason:

   > $approval_reason

   Let the host decide. Use the ordinary sandboxed context when eligible automatic review is unavailable and sandbox access is not already known to fail. Report an unavailable route or denied request as a capture gap so routine maintenance stays noninteractive. Keep the request scoped to the emitted collection command and retain the actual error or review reason.
3. Treat `$receipt` as usable only when this call completed successfully and the receipt reports `status=captured`. Report its capture gaps. On failure keep the original error and any receipt the collector wrote. Cancellation ends this attempt; report unknown host or process outcomes to the parent.
