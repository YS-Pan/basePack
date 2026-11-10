# Cases

These situations illustrate the evidence and responsibility behind a decision. Read the cases relevant to the current task; their local facts determine the result.

## Required fields and valid absence

A worker receipt promises a start time once a job has started. Replacing a missing start time with zero creates a plausible duration while hiding a broken receipt. Read the required value directly so the failure identifies the producer or contract that needs repair. If the job has never started, represent that documented state as such.

A scheduler also describes machines that have no GPU. Its contract makes GPU attributes optional on those machines, with absence meaning zero GPU capacity. Supplying that value is valid normalization at the boundary. Changing every optional lookup to a required lookup would break legitimate CPU machines. The field's meaning, rather than the lookup syntax, decides the handling.

## A lost submission response

A scheduler accepts jobs with a caller-generated unique token. The submit command loses its response after the scheduler might have accepted the job. Repeating the command could duplicate expensive work.

The client can handle this known failure by looking up that token. An unambiguous match supplies the actual job ID and confirms submission; the recovered result has the same meaning as a normal submission result. If the lookup fails or leaves the outcome unresolved, preserve the original submission error and any lookup failure so the caller can act on the real uncertainty. Recovery earns its place through confirmed state, rather than through a generic retry or a newly invented success category.

## Scheduling and shared capacity

A client knows the requested CPU and memory amounts, while a scheduler owns machine matching, admission, and queueing. Available capacity can change between a client query and submission. Let the client enforce its request schema and let the scheduler queue valid work. Add a client restriction only for a responsibility the client actually owns, such as an application constraint the scheduler cannot express.

Two independent services sharing one GPU still need a real combined memory budget. Each may allocate outside the other's scheduler, so an administrator must assign limits appropriate to their workloads. One successful request does not establish the peak of both services together. Removing a duplicate scheduling check and retaining a shared-resource budget follow the same rule: place the decision with the owner who has the necessary information and control.

## Compatibility by feature and evidence

A lightweight client has completed its normal workflow on a newer Python release, but an optional model extra depends on a package that cannot install there. An upper bound on the whole client would block a working use case. Scope the known conflict to the extra and keep the client declaration consistent with its actual dependencies and supported operation. Success of the lightweight workflow provides evidence for that workflow; the extra retains its separate condition.

Similarly, testing on one GPU model establishes a dated example. Installation instructions should describe the model's required operations, supported runtime, and memory demand. A genuine dependency on a specific architecture belongs in the requirements; the name of the author's machine belongs in development observations. An untried machine remains an unknown until relevant evidence resolves it.

## Operational information beside the action

An embedding request times out on the client while inference continues in a shared service. The instruction that timeout ends waiting is necessary: the user must understand the ongoing resource use and whether to wait, inspect, or stop work through a supported control.

A repeated statement that a diagnostic command cannot prove every workload adds little when the next step already performs the chosen operation. State what the diagnostic checks, give the operation and expected result, and put broader experimental coverage in development records. Keep the explanation that changes a decision; give the reader an action when it matters.

## Completion for the intended use

A person installing a selected feature needs its prerequisites and a short successful operation showing that it works. Developer comparisons across devices and failure experiments belong to development work. If the person is configuring shared infrastructure, the capacity decision above is part of that task and remains necessary.

Another requested artifact may be a guide whose usefulness will emerge through extended real use. When the user chooses that basis, deliver the usable guide and route later observations into its existing maintenance records. A small artificial exercise answers a different question; file format checks establish only the file's format. Choose evidence to fit the claim being made and finish the authorized deliverable.
