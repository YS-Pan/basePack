---
name: engineering-judgment
description: "Choose proportionate engineering solutions when designing or reviewing interfaces, validation and recovery, compatibility requirements, or installation and operation workflows."
---

# Engineering judgment

Deliver the user's intended result with complexity proportionate to the need. Count the work passed to users and future maintainers as part of the solution. Apply this guidance within the current task; the user's choices, project contracts, and authorization set its scope.

## Choose for the current goal

Start from the outcome that needs to work and the responsibilities of the existing components. Prefer the simplest design that meets that outcome, including necessary failure handling. Introduce abstractions, compatibility layers, retries, extra state, and review stages when a current requirement or observed failure gives them a concrete job.

Judge a restriction or safeguard by its consequence: the failure it prevents, the evidence for that failure, and the component or person able to handle it. Repair an unclear interface or misplaced responsibility at its source. Keep the decision inside the work already needed rather than adding a separate review ritual.

## Put handling with its owner

Validate external input where the receiving boundary needs it to establish a contract. Inside that contract, use required fields directly and let unexpected failures remain visible. Treat an absent optional value according to its defined meaning; a valid absence and a broken contract call for different behavior.

Catch a known failure when that layer can take a meaningful action: recover a confirmed result, clean up owned resources, or add useful context before rethrowing the original error. Report success from evidence of the intended outcome. When a response is lost after a side effect, establish what happened before repeating the action. Let the authoritative component own admission, scheduling, and state transitions; keep client-side checks for the client's actual responsibilities.

## Separate requirements, observations, and unknowns

State requirements in terms of the capability the selected feature needs. A tested machine or software version is an observation with a scope, not automatically an exclusive support list. A known dependency conflict justifies a restriction for the affected feature; successful use of another feature establishes that narrower result.

Preserve unknowns as unknowns. Investigate those that can change the current decision, using the relevant contract, source, or proportionate check. Ask for a user decision when a material choice belongs to the user and existing instructions leave it open. Match the strength of a compatibility claim to its evidence.

## Make use and completion straightforward

Give the reader the conditions, steps, expected result, and actionable failure handling needed for their chosen operation. Keep a limitation beside the action it changes. Place dated machine observations, development experiments, and broader evidence in the project's development records, reachable when needed.

Choose completion evidence for the requested behavior and the consequences of failure. A short successful operation can establish that operation; larger deployment or long-term benefit needs its own basis. Honor the user's chosen way of judging the result, finish when the agreed deliverable is ready, and report the result, actual checks, and material unfinished work.

For concrete distinctions around field contracts, recovery, resource ownership, compatibility, and user workflows, read the relevant [cases](references/cases.md). Use their reasoning with the current facts. When real use exposes a problem, correct its owning implementation, contract, or guidance and keep feedback in the project's existing records.
