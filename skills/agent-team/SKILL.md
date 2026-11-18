---
name: agent-team
description: "Choose and manage the organization for every task, from solo work and direct collaboration to clear multi-level teams."
---

# Agent teams

Apply this skill to every task, including work the main agent completes alone. Expand task capacity and improve result quality by keeping each agent's context focused. The main agent owns the goal, key decisions, and overall result. Use the host's subscription-based subagent tools when delegation helps, without adding a model API or orchestration service.

## Choose the organization

Before execution, imagine the entire authorized deliverable is complete and look back at the work needed to reach it: likely stages, dependencies, ordinary rework, verification, and recovery. Choose for that whole course of work:

- What would fill the main agent's context and attention? Would routine dispatch, preparation, debugging, or integration crowd out its overall judgment?
- Which sustained branches could a coordinator own through completion, including follow-up work and dependencies?
- Would that division improve capability, result quality, and focus enough to justify handoff costs, delay, and information loss?

Choose solo work, a few directly managed collaborators, clear coordinator-worker layers, or a mix across branches and phases. Direct collaboration can combine roles. Prefer a simpler structure when expected results are comparable, considering the whole delivery rather than just startup effort. Keep the choice lightweight: a brief mental decision for small tasks, a short statement of structure and reason for substantial work.

Revise the choice when new scope, evidence, dependencies, or actual workload changes its basis. When uncertainty prevents a useful whole-task judgment, use bounded exploration to clarify the work before choosing its continuing organization. Run ready, independent work in parallel; sequence dependent work and leave spare capacity when useful.

- Resolve the project's AI level before dispatch. In a basePack project, use the Python and explicit config from `.basepack/instructions.md`. `python -m basepack --config <project-config> config ai` resolves the routine default, initially level 3. `config ai --level 3` selects that level explicitly. Choose a configured level by task difficulty and user preference. Pass the returned `model` and `reasoning_effort` explicitly through host parameters.
- In projects without an AI mapping, select from actual host capabilities and user preferences. Use the host's delegation, nesting, context and model controls. Report unavailable mappings or capabilities and preserve original tool errors. State any model or level substitution explicitly. Report a task as dispatched after actual host creation.

## Delegate a complete brief

Start a new topic with a self-contained brief and explicitly select clean history (`fork_turns="none"` where supported). Include task-relevant context and binding constraints in the brief itself; reuse the same worker for related follow-up.

```text
Goal and use: required result, completion criteria, and the decision or stage it feeds.
Scope and context: binding constraints, known findings, sources, permitted edits.
Ownership: branch dispatcher, dependencies, output owners, decisions and delegation allowed.
Delivery: files to produce or update, and the short return below.
```

Let the recipient search, read broadly, and fill relevant gaps within scope. Assign paths for substantial results using the project's conventions: deliver code and documents in their owning files, and intermediate reports in project-local temporary storage such as `tmp/<task>/`. Small results can stay inline.

## Coordinate and execute

1. **Own a layered branch.** Assign its coordinator continuing responsibility for routine delegation, follow-up, dependencies, normal fixes, verification, and integration through branch completion, including arranging the next work. The coordinator delegates further within its authority; the main agent exchanges goals, results, and issues requiring key decisions, and may inspect sources or intervene. Keep one dispatcher for that branch. When ownership changes, explicitly hand over active tasks and handles, dependencies, outputs, and open issues.
2. **Split reading, then connect evidence.** Assign semantically related, nonoverlapping finite source groups. Each author owns the group's reading, interpretation, relationships, and ordinary repairs through a complete delivery; size groups by their connections and manageable scope. Track coverage and unread areas. Bring relevant passages into one agent's context for claims that depend on relationships across groups; arrange targeted follow-up reading where evidence is missing.
3. **Assign output ownership.** Give shared files or artifacts one integration owner. Parallelize edits with independent ownership; run dependent checks when their inputs are ready. Arrange overlapping investigation or independent review for a stated purpose.
4. **Finish bounded work.** Workers read, execute, and perform necessary checks, then return when their completion criteria are met. Resolve gaps within authority; escalate facts, impact, and the decision needed when goals, key tradeoffs, or permissions must change.
5. **Collect results through events.** Continue independent work while children run. Observe owned handles or your branch only; use host completion events or bounded waits, continuing the wait after an unchanged timeout. Read necessary slices of instructions and receipts. Intermediate messages carry errors, dependencies, or changes needing early action; return usable results at the agreed boundary.

Add specialist review when uncertainty, material risk, or task requirements justify it. Batch related results and keep checks proportionate to the problem.

## Integrate and complete

Return selected findings in a short form:

```text
Conclusion and conditions:
Counterevidence, conflicts, and unfinished scope:
Evidence and artifact locations; actual changes and checks:
```

Keep decision-critical premises in this return. Downstream agents read original artifacts directly; pass their locations rather than repeatedly rewriting full reports through each coordinator. For snapshot handoffs, deliver once with the assignment and fixed artifact references, including hashes when required; preserve those snapshots and use a new file/hash for revisions. Recognize a later automatic final for the same delivered references as the same completion; a revised reference is a new delivery.

At the decision or stage that consumes a result, reconcile its conditions, counterevidence, and gaps: integrate it, request a targeted follow-up, or explain why it is set aside. Derive completion claims from actual artifacts and checks. The main agent owns key decisions and the overall deliverable.

For long branches, hand off at a completed source-group or stage boundary: save results, open scope, dependencies, and actual handle authority, finish the old group's in-flight work, then create the next coordinator with clean history and a new identity. When the host cannot transfer reader handles, complete the old group and create new readers. A summary in the same context is a continuation, not clean history. Keep the original parent lifecycle and stop authority; the main agent receives stage results and key decisions while the coordinator owns routine dispatch.

When work needs continuation across turns or interruptions, record the goal, established findings, active tasks and handles, open issues, and next steps in existing project progress materials. Before task closure, retain needed conclusions and selected evidence in their stable project locations and update references; temporary handoffs may then be cleared.

Evaluate capability and result quality first: work that was previously infeasible, correctness, completeness, and judgment quality. Record main-agent context and round trips, total team usage, and elapsed time separately. Higher usage is acceptable for better results; usage savings are not a success criterion. Mark unavailable usage data as unknown.
