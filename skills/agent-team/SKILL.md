---
name: agent-team
description: "Organize hierarchical agent teams for broad reading, synthesis across sources, or multi-step work that benefits from focused contexts and delegated coordination."
---

# Agent teams

Expand task capacity and improve result quality by giving each agent a focused context. The main agent owns the goal, key decisions, and overall result; coordinators handle routine delegation and integration. Use the host's subscription-based subagent tools without adding a model API or orchestration service.

## Choose the organization

- Complete small tasks directly. The main agent may assign a few bounded subtasks itself. Delegate a branch to a coordinator when reading waves, dependencies, or integration would demand substantial routine management.
- Adjust team size, depth, and roles as the task evolves. Run ready, independent work in parallel; sequence dependent work and leave spare capacity when useful.
- Match available models and reasoning effort to difficulty. Lower-cost models may handle broad reading and extraction; use sufficient capability for complex execution, synthesis, and decisions. Honor user preferences and select concrete models through host parameters or role configuration.
- Use the tools' actual delegation, nesting, context, and model controls. Report missing required capabilities and preserve original tool errors. Distinguish a prepared brief from a task that actually ran.

## Delegate a complete brief

Start a new topic with a self-contained brief and explicitly select clean history (`fork_turns="none"` where supported). Include task-relevant binding constraints in the brief itself. Inherit history when the task needs it; reuse the same worker for related follow-up.

```text
Goal and use: required result, completion criteria, and the decision or stage it feeds.
Scope and context: binding constraints, known findings, sources, permitted edits.
Ownership: branch dispatcher, dependencies, output owners, decisions and delegation allowed.
Delivery: files to produce or update, and the short return below.
```

Let the recipient search, read broadly, and fill relevant gaps within scope. Assign paths for substantial results using the project's conventions: deliver code and documents in their owning files, and intermediate reports in project-local temporary storage such as `tmp/<task>/`. Small results can stay inline.

## Coordinate and execute

1. **Own the branch.** Give each branch one dispatcher. The coordinator owns its routine delegation, follow-up, dependencies, and integration, delegating further within its authority. Transfer dispatch ownership explicitly when it changes. The main agent exchanges goals and results with the coordinator and may inspect sources or intervene when needed.
2. **Split reading, then connect evidence.** Partition by question or materials and track coverage and unread areas. Bring relevant passages into one agent's context for claims that depend on relationships across partitions; arrange targeted follow-up reading where evidence is missing.
3. **Assign output ownership.** Give shared files or artifacts one integration owner. Parallelize edits with independent ownership; run dependent checks when their inputs are ready. Arrange overlapping investigation or independent review for a stated purpose.
4. **Finish bounded work.** Workers read, execute, and perform necessary checks, then return when their completion criteria are met. The responsible coordinator continues the next stage. Resolve gaps within authority; escalate facts, impact, and the decision needed when goals, key tradeoffs, or permissions must change.
5. **Collect results through events.** Continue independent work while children run. When results are needed, use the host's agent wait or completion notifications. Coordinators handle routine follow-up and report usable results, significant changes, or issues requiring parent intervention.

Add specialist review when uncertainty, material risk, or task requirements justify it. Batch related results and keep checks proportionate to the problem.

## Integrate and complete

Return selected findings in a short form:

```text
Conclusion and conditions:
Counterevidence, conflicts, and unfinished scope:
Evidence and artifact locations; actual changes and checks:
```

Keep decision-critical premises in this return. Downstream agents read original artifacts directly; pass their locations rather than repeatedly rewriting full reports through each coordinator.

At the decision or stage that consumes a result, reconcile its conditions, counterevidence, and gaps: integrate it, request a targeted follow-up, or explain why it is set aside. Derive completion claims from actual artifacts and checks. The main agent owns key decisions and the overall deliverable.

When work needs continuation across turns or interruptions, record the goal, established findings, active tasks and handles, open issues, and next steps in existing project progress materials. Before task closure, retain needed conclusions and selected evidence in their stable project locations and update references; temporary handoffs may then be cleared.

Evaluate capability and result quality first: work that was previously infeasible, correctness, completeness, and judgment quality. Record main-agent context and round trips, total team usage, and elapsed time separately. Higher usage is acceptable for better results; usage savings are not a success criterion. Mark unavailable usage data as unknown.
