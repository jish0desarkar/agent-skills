---
name: design-system
description: 'Use whenever generating, modifying, or reviewing ANY frontend code in a repo that has a design system — templates, partials, components, snippets, or CSS. Enforces the UI contract in DESIGN.md (or the repo''s equivalent): only use predefined primitive classes (e.g. ui-*) and design tokens, compose before inventing, add the fewest classes possible, and make loading skeletons mirror real content. If a design or screenshot needs a primitive that does not exist, stop and ask the user before adding it. Can also bootstrap a DESIGN.md from an existing stylesheet.'
---

# Design System Compliance

All UI work in this repo is governed by a strict contract. Follow it exactly — non-compliant output is rejected.

**Precedence:** the repo's design contract and its tokens/primitives stylesheet supersede any other frontend or aesthetic guidance (including generic "make it beautiful" design skills or plugins). Do not introduce new fonts, colors, gradients, or visual flourishes outside the existing token system. Consistency with the design system wins over creative expression here.

This skill uses `ui-*` as the primitive-class prefix and `--color-*` as the token prefix. If the repo uses different prefixes, substitute them everywhere below.

## 1. Read the source of truth FIRST

Before writing any UI code, find and read:

| What | Usually |
|---|---|
| The UI contract — hard rules, not guidelines | `DESIGN.md`, `docs/design-system.md`, or the design section of `AGENTS.md` |
| Every design token and every primitive class | `design-system.css`, `tokens.css`, `theme.css`, or the Tailwind theme config |
| The base layout that consumes them | The main layout/shell template or root component |
| Tailwind → token mapping (if Tailwind is used) | `tailwind.config.*` theme colors, or a colors JSON it imports |

These files override anything you assume. If none of them exist, see §8 before writing UI code.

## 2. Only use classes that already exist

- Every reusable primitive (buttons, inputs, pills, cards, typography, loaders, side panels, alerts) **must** use the matching `ui-*` class.
- **Never invent a class name.** Before using any `ui-*` class, confirm it actually exists in the stylesheet (`rg -n '\.ui-btn' path/to/design-system.css`). If you cannot find it there, it does not exist — do not use it.
- Compose existing classes to reach a result before considering anything new.
- No hardcoded hex/RGB/named colors. Use the design tokens (prefer a `ui-*` class over a raw `var(--color-*)`).
- No template-local `<style>` blocks for primitives that already exist. Page-local CSS is allowed only for genuinely unique layout/flow that no existing class can express.
- Forbidden: page-scoped primitive classes like `view-btn-*`, `prompt-btn-*`, `action-btn`, `card-custom`, `my-input`. Replace any you find with their `ui-*` equivalent.
- If Tailwind is used, color utilities must map to design tokens through the theme config — never use Tailwind's default palette (`bg-blue-500`, `text-gray-700`, etc.).

## 3. Use the minimal set of classes

Add only the classes strictly required to satisfy the feature. Do not pile on layout or utility classes "to be safe."

- Reach for the simplest construct that works. If a fixed-height parent can be filled with a single `h-full`, do **not** build a `flex` / `flex-1` / `min-h-0` scaffold to achieve the same result.
- Every class must earn its place: if removing it does not change the rendered result or behavior, remove it.
- Do not add defensive or redundant utilities — e.g. `min-h-0` when an adjacent `overflow-hidden` already zeroes the flex auto-minimum. Redundant-but-harmless is still clutter.
- Applies to Tailwind utility classes too, not just `ui-*` primitives.
- Do not assume a utility "cannot" override a primitive because of cascade layers — check in the browser before adding workarounds.

## 4. When a needed class does NOT exist — STOP and ask

If a design, screenshot, or requirement needs a primitive or class that is **not** in the stylesheet:

1. Do **not** silently add it, inline it, or fake it with custom CSS.
2. Ask the user before adding anything to the stylesheet (in Claude Code use the **AskUserQuestion** tool; elsewhere ask in chat and wait). Include:
   - what the design needs and which existing class is the closest fit,
   - the exact new class you propose (name following `ui-{category}-{modifier}`, plus the CSS, using tokens only),
   - the alternative of composing existing classes instead.
3. Only after the user approves, add the new primitive **once** in the stylesheet (never in a template), consume it by class name, and document it in the contract under the right section.

## 5. Preserve behavior when migrating

When touching a file with legacy classes, migrate it fully to `ui-*` (no half-migrated mixes). Keep all behavior bindings intact — HTMX attributes, Alpine.js directives, Stimulus controllers, React/Vue props and event handlers, `data-*` hooks used by scripts or tests. Change styling only, never logic, unless a redesign was explicitly requested.

## 6. Skeleton / shimmer loaders must mirror the content they replace

A loading skeleton is a placeholder for one specific piece of content — its job is to preview that content's layout so nothing visibly shifts when the real content swaps in. Build the skeleton from the real element's markup, not as a generic blob.

- Match the **structure**: same outer wrapper (`ui-card`, `flex`, `gap-*`, padding) and the same regions in the same order as the loaded element. A single full-width bar standing in for a multi-column card is wrong — that mismatch is the layout jump reviewers flag.
- Match the **dimensions**: reuse the real element's sizing utilities (`flex-1`, `min-w-*`, fixed widths, avatar size) so each placeholder occupies the same footprint as the thing it replaces.
- Build placeholders only from the existing loader primitives (for example `ui-loader-bar`, `ui-loader-avatar`, `ui-spinner`). Do not invent new shimmer shapes; if none fit, STOP and ask per §4.
- When you change the real element's layout, update its skeleton in the same change so the two never drift apart.

## 7. Before finishing — run the checklist

If the contract has its own pre-submission checklist, run that. Otherwise verify:

- [ ] Typography, buttons, inputs, pills, cards, alerts and loaders all use `ui-*` primitives
- [ ] Every `ui-*` class used exists in the stylesheet (grep each new one)
- [ ] No hardcoded colors; Tailwind colors (if any) map to tokens
- [ ] No new in-template primitive CSS; no page-scoped primitive classes
- [ ] No class that can be removed without changing the result
- [ ] Any new shared primitive was user-approved, added once to the stylesheet, and documented
- [ ] Legacy classes in touched files fully migrated
- [ ] Behavior bindings (HTMX/Alpine/JS handlers/test hooks) intact
- [ ] Skeletons match the structure and footprint of their content

## 8. No contract yet? Bootstrap one (only when asked or agreed)

If the repo has a stylesheet with reusable classes but no written contract, offer to create `DESIGN.md` instead of guessing:

1. Inventory tokens (`rg -o -- '--[a-z0-9-]+(?=:)' -P <css>`) and primitive classes (`rg -o '^\.[a-z][a-z0-9-]+' <css> | sort -u`), grouped by category.
2. Find the legacy one-off classes and inline colors that duplicate them (`rg -n '#[0-9a-fA-F]{3,6}\b' templates/ src/`).
3. Write the contract: token table, one section per primitive category with a usage snippet, the rules in §2–§6, and a pre-submission checklist.
4. Show the draft before saving. Do not rename or delete existing classes as part of bootstrapping.
