# Build With Ownership — Claude Code Skill

A manually invoked Claude Code workflow for implementing features with agents while preserving architectural understanding, debugging ability, and human ownership.

## Recommended setup

Use this as one skill with supporting files. Do not create a separate skill for every workflow phase initially. The phases share state and decisions, and loading one coherent skill keeps the contract, design, implementation, verification, and knowledge reconstruction connected.

Split out a companion skill later only when a phase becomes useful independently and repeatedly, such as:

- hypothesis-driven production debugging;
- adversarial diff review;
- post-feature knowledge quiz.

## Install for all projects

Copy the entire `build-with-ownership` directory to:

```bash
mkdir -p ~/.claude/skills
cp -R build-with-ownership ~/.claude/skills/build-with-ownership
```

Then invoke it inside a repository:

```text
/build-with-ownership Add an authenticated POST /jobs endpoint with idempotency and a per-user active-job limit
```

## Install only in one project

```bash
mkdir -p .claude/skills
cp -R build-with-ownership .claude/skills/build-with-ownership
```

Commit the folder when you want the workflow shared with the team.

## Suggested usage

### Feature

```text
/build-with-ownership Add scheduled webhook delivery with retries and an outbox
```

### Bug

```text
/build-with-ownership Diagnose why accepted jobs sometimes never reach BullMQ
```

### Refactor

```text
/build-with-ownership Refactor the billing webhook handler without changing behavior
```

### Review

```text
/build-with-ownership Review the current diff against the issue and identify correctness risks; do not edit
```

### Quiz

```text
/build-with-ownership Quiz me on the feature in the current branch, one question at a time
```

## Why manual invocation is enabled

The skill has `disable-model-invocation: true`. This prevents Claude from deciding on its own to start a long, stateful workflow. You explicitly choose when to use it.

## Permissions

The skill deliberately does not pre-approve tools. Keep your normal Claude Code permission settings so file edits and shell actions remain visible and governed by your existing controls.
