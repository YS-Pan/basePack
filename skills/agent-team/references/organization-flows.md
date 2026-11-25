# Agent team diagrams

## Default structure with 12 free slots

The main agent owns the goal, key decisions, and overall delivery. Each coordinator manages dispatch, dependencies, follow-up, verification, and integration for its branch. Workers carry out the assigned work. The 12 slots count subagents at every level.

```mermaid
flowchart TB
    main[Main agent]
    main --> direct1[Direct worker 1]
    main --> coordA[Dedicated coordinator A]
    main --> coordB[Dedicated coordinator B]
    main --> direct2[Direct worker 2]
    coordA --> a1[Worker A1]
    coordA --> a2[Worker A2]
    coordA --> a3[Worker A3]
    coordA --> a4[Worker A4]
    coordB --> b1[Worker B1]
    coordB --> b2[Worker B2]
    coordB --> b3[Worker B3]
    coordB --> b4[Worker B4]
```

## Size teams to available slots

The main agent sizes teams to the host's free slots and the remaining work. Each coordinator dispatches workers within its assigned budget.

```mermaid
flowchart TB
    seats[Check free slots and remaining work] --> enough{"Would layering help, and are enough slots free?"}
    enough -->|No| direct[Work solo or delegate directly]
    enough -->|Yes| groups[Aim for four workers per coordinator]
    groups --> quota[Set worker budgets and leave spare slots free]
```

## Reassess the team and hand off a branch

Record active tasks and handles, dispatch authority, dependencies, and open issues in the handoff. If the host cannot transfer handles, the original parent collects the in-flight results before handing over further dispatch. The original parent retains lifecycle and stop authority for agents it created. Assign one dispatcher per branch.

```mermaid
flowchart TB
    kickoff[Before starting, work backward from delivery] --> assess[Choose a structure for the remaining work]
    reassess["Before a new stage or another round of direct dispatch on the same branch"] --> assess
    assess --> sustained{"Does the branch need sustained coordination?"}
    sustained -->|No| direct[Work solo or delegate directly]
    sustained -->|Yes| assign[Assign a dedicated coordinator and hand off as needed]
    assign --> branch[Coordinator dispatches, follows up, and verifies results]
    branch --> main[Main agent receives stage results and issues that need decisions]
    direct --> next{"What comes next?"}
    main --> next
    next -->|Reassessment point| reassess
    next -->|Work complete| delivery[Main agent delivers the overall result]
```

## Choose a subagent model

```mermaid
flowchart TB
    task{"What kind of dispatch?"}
    task -->|Memory maintenance or dedicated retrieval| specialist[Use the model specified by that workflow]
    task -->|General task| override{"Did the user or assignment specify a model?"}
    override -->|Yes| specified[Use the specified model]
    override -->|No| inherit[Use the immediate parent's current model]
```
