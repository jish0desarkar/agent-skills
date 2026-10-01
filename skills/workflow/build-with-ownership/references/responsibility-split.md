# Responsibility Split

Use this as a decision rule, not as a rigid ban on assistance.

## The human engineer owns

- The intended product behavior.
- Acceptance criteria and non-goals.
- Important invariants.
- Trust boundaries and authorization semantics.
- Source-of-truth decisions.
- Transaction and consistency model.
- Concurrency, ordering, retry, and idempotency semantics.
- Whether a dependency or abstraction is justified.
- Operational risk, rollout, and rollback decisions.
- The first debugging hypothesis and investigation direction for production defects.
- Final approval.

Claude may propose and critique these decisions, but must not silently make them.

## Claude may lead

- Repository reconnaissance.
- Locating similar implementations and tests.
- Mechanical code generation.
- DTOs, adapters, serializers, fixtures, and repetitive mappings.
- Migration boilerplate after schema semantics are approved.
- Repetitive test implementation after scenarios are approved.
- Command execution and result collection.
- Static analysis and adversarial review.
- Documentation drafts.
- Generating questions and quizzes.

## Shared work

- Design alternatives.
- Failure-mode analysis.
- Test strategy.
- Diff review.
- Performance analysis.
- Security review.
- Debugging after the human has formed an initial model.

## Delegation rule

The engineer does not need to remember syntax or every library API. The engineer must understand why the change is designed this way, where state lives, how the system transitions, what can fail, and how it recovers.

Never delegate a decision the engineer cannot explain afterward.
