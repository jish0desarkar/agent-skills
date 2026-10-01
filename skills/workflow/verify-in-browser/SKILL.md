---
name: verify-in-browser
description: Verify a web-app change at runtime by launching an isolated instance of the app on the current code (next to the shared dev stack, without disturbing other agents) and driving it in a real or headless browser, reporting evidence — screenshots, DOM state, console and network errors — instead of "should work". Use when asked to verify, smoke-test or check a UI/HTTP change in the running app, or before declaring a user-facing change done.
---

# Verify a change in the real app

Static checks prove the code parses. Only the running app proves the change works. This
skill gets your code running in isolation, drives it like a user, and reports what it saw.

## 1. Do not trust the already-running server

The shared dev server is often **not running your code**: it may lack auto-reload, run from
another branch or worktree, or belong to another agent session. Before verifying anything,
check what it runs. If in doubt, start your own instance.

**Docker Compose stacks** — reuse the running app's image, env and network, but mount your
checkout and use your own name and port:

```bash
docker inspect <app-container> --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -v '^$' > "$SCRATCH/app.env"
docker run -d --name <app>-verify-<tag> --network <compose-network> -p 80XX:<app-port> \
  --env-file "$SCRATCH/app.env" -v "$PWD":/app -w /app \
  <app-image> <start command, e.g. uvicorn main:app --host 0.0.0.0 --port <app-port>>
```

**Plain dev servers** — start a second process on a free port (`uvicorn ... --port 80XX`,
`npm run dev -- --port 51XX`) from your checkout.

Then:

- Wait for readiness with a health endpoint or `curl` loop, not a fixed sleep. Some apps log
  nothing until ready.
- Keep the env file in a scratch directory, never in the repo — it contains secrets.
- **Know what still runs old code.** Background workers, schedulers and queue consumers are
  usually still the shared ones. A change to a task is not verified by a new web container;
  say so, or start an isolated worker too.
- Never point the instance at production data. Prefer the dev database; isolate further
  if the check writes data.
- Remove your container/process when done (`docker rm -f <app>-verify-<tag>`), and never
  stop containers other sessions may be using.

## 2. Authenticate safely

- A browser that is already signed in to `localhost` usually works on your port too —
  cookies are scoped by host, not port.
- For a headless browser, create a test session the way the app does: insert a session
  row for a **test** user and sign/encrypt the cookie with the app's own helper, run inside
  the app container. Do not hand-roll the crypto — apps often have several keys, and the
  wrong one fails silently. Delete the session afterwards.
- Never type real user passwords or production credentials.

## 3. Drive the browser

Use the agent's browser tool if it has one. For layout-, animation- or timing-dependent
checks, prefer a **headless Chromium** (Chrome, Brave, Edge) started with
`--headless=new --remote-debugging-port=<port>` and driven over CDP — Playwright if the
project has it, otherwise Node ≥ 22's built-in `WebSocket`.

**Gotcha — hidden panes stall animation frames.** When an embedded browser pane is hidden,
`document.visibilityState` is `hidden` and `requestAnimationFrame` never fires. Transition-
driven UI (Alpine `x-show`, Vue/React transition groups) then stays `display:none`, which
fakes layout bugs such as 0-height iframes. Check `document.visibilityState` before believing
a layout bug; switch to headless if it is `hidden`.

**Wait on state, not time.** Wait for the condition the user would see: an element, a store
flag (`Alpine.store('x').loading === false`), `htmx:afterSettle`, network idle — never a bare
sleep.

**Load fragments directly when the UI path is long.** For HTMX-style apps you can reproduce
exactly what a click does with `htmx.ajax('GET', '/fragment/url', {target: '#panel'})`;
in SPAs, navigate to the route. Use the same sequence the real template uses so the check
stays honest.

## 4. What to check

- The changed behavior, on the happy path **and** one failure or empty state.
- Console errors and warnings introduced by the change.
- Network: no unexpected 4xx/5xx, no duplicate requests, correct fragment targets.
- Layout: no shift when loaders swap to content; narrow width (~375px) when the UI is responsive.
- Persistence: reload the page — does the state survive as intended? Inspect the database or
  draft store directly when the UI cannot show it.

## 5. Report evidence

State what you ran, what you saw (screenshot or DOM/console excerpt), and what you did **not**
verify (old worker code, untested browser, skipped flow). "Verified" means you watched it work.

## 6. Record repeatable flows

The first verification in a repo is slow; the second should not be. When you discover a
reliable recipe — container command, auth step, how to open a panel, where drafts are stored,
the DB shell command — offer to add it under a **Runtime verification** section in the
project's `AGENTS.md`/`CLAUDE.md`, and read that section first next time. Example:

```markdown
## Runtime verification
- Isolated web container: see verify-in-browser §1; network `myapp_default`, image `myapp-web`, port 80.
- Settings chat: open `/settings`, type in `#chat-input`, Enter; wait for `Alpine.store('chat').streaming === false`.
- Drafts: SQLite at `/data/<account>/cache.db`, table `drafts`.
- DB shell: `docker compose exec db psql -U postgres -d myapp`.
```
