---
name: engineering-judgment
description: "Use when designing or reviewing data models, module boundaries, interfaces, validation, failure handling, compatibility, or operation workflows."
---

# Engineering judgment

Choose the simplest design that delivers the user's intended behavior. Count the work it leaves to callers, operators, and future maintainers. Follow the user's choices, project contracts, and task scope.

## Model the data

Start with the facts the system must store and the operations it must support. Keep a property on its record when it shares that record's lifecycle. Give a relationship explicit endpoints and a type when it needs independent traversal, reference, or management. Share representation and operations where the contract is shared. Preserve each type's meaning, constraints, and conditions.

Give each fact one authoritative representation. Derive other views from it and keep stored indexes rebuildable. When history matters, distinguish stable identity, exact revision, source location, and mutable current state. Give independently changing facts separate representations when that difference affects a read or write.

When a modeling choice changes stored data or caller behavior, trace the smallest real example that distinguishes the designs through write, read, and update. Choose the target contract from intended use. Plan migration against that contract, preserving the identities and evidence callers still need.

## Give each rule an owner

Put each invariant and state transition where it can be enforced using authoritative data. Reuse the existing module, database, or service when it already owns the operation. Keep its rules behind a direct interface so callers can use them consistently.

Add a module or wrapper when it owns a distinct responsibility or removes repeated coordination from callers. Prefer native operations and direct calls. Give every added layer, copy of state, compatibility path, and retry a concrete job tied to a current requirement or observed failure.

## Let it crash inside the contract

Validate external inputs where the receiver establishes the contract. Enforce write invariants where the authoritative state changes. Inside the contract, read required values directly. Use defaults for documented optional values with a defined meaning.

Let unexpected failures propagate with their original cause. Catch a specific failure when the layer can recover a confirmed result, clean up resources it owns, or add actionable context and rethrow. If an operation may already have committed, check the authoritative result. Retry when the contract makes repetition safe. Surface unresolved outcomes as uncertain.

## Fit the actual use

Scope compatibility to the capability and the evidence. Resolve unknowns that could change the design. Put prerequisites, expected outcomes, and actionable limits next to the operation they affect. Verify the requested behavior through its normal entry point and report material open issues.

For examples of relationship modeling, versioned identity, boundary errors, resource ownership, and compatibility, read the relevant [cases](references/cases.md).
