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

Send the necessary goal and context in one concise brief. Reuse valid background already available to the recipient.

```text
Goal and completion: the required result and how to recognize completion.
Scope and context: constraints, known findings, source locations, permitted edits.
Coordination: dependencies, shared-output owners, decisions and further delegation allowed.
Return: usable conclusions, key evidence and locations, actual checks, unresolved issues.
```

Let the recipient search, read broadly, and fill relevant gaps within scope before returning selected results. Start new topics with a clean context and the necessary background; continue the same worker for related follow-up work. Where supported, use `fork_turns=none` for a clean start and inherit history when the task needs it.

## Coordinate and execute

1. **Own the branch.** The coordinator assigns bounded work with source scope, dependencies, outputs, and owners, delegating further within its authority. The main agent normally exchanges goals and results with the coordinator and may inspect sources or intervene when needed.
2. **Split reading, then connect evidence.** Partition by question or materials and track coverage and unread areas. Bring relevant passages into one agent's context for claims that depend on relationships across partitions; arrange targeted follow-up reading where evidence is missing.
3. **Assign output ownership.** Give shared files or artifacts one integration owner. Parallelize edits with independent ownership. Arrange overlapping investigation or independent review for a stated purpose, with one dispatcher for each review.
4. **Finish bounded work.** Workers read, execute, and perform necessary checks, then return when their completion criteria are met. The responsible coordinator continues the next stage. Resolve gaps within authority; escalate facts, impact, and the decision needed when goals, key tradeoffs, or permissions must change.
5. **Collect results through events.** Continue independent work while children run. When results are needed, use the host's agent wait or completion notifications. Coordinators handle routine follow-up and report usable results, significant changes, or issues requiring parent intervention.

Add specialist review when uncertainty, material risk, or task requirements justify it. Batch related results and keep checks proportionate to the problem.

## Integrate and complete

Return conclusions with their conditions, necessary evidence and source locations, coverage and gaps, and actual changes and checks where relevant. Preserve decision-relevant disagreements and uncertainty. Include key premises with the conclusions; use links for tracing and deeper reading.

The coordinator reconciles dependencies and findings across sources, checks its completion criteria, and identifies unfinished scope before returning. The main agent makes key decisions from the selected evidence and owns the overall deliverable, reading original sources as needed.

When work needs continuation across turns or interruptions, record the goal, established findings, active tasks and handles, open issues, and next steps in existing project progress materials. Keep task state in its owning project.

Evaluate capability and result quality first: work that was previously infeasible, correctness, completeness, and judgment quality. Record main-agent context and round trips, total team usage, and elapsed time separately. Higher usage is acceptable for better results; usage savings are not a success criterion. Mark unavailable usage data as unknown.
