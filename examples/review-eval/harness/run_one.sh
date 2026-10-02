#!/bin/bash
# usage: run_one.sh review <pr-id> <arm>   |   run_one.sh map <map-id>
# One headless Claude Code session in a clean environment: no user settings, no MCP, no web tools,
# Bash sandboxed (no network, writes only in the checkout), and `gh` replaced by the offline stub.
EV="$(cd "$(dirname "$0")" && pwd)"
kind=$1

# Boundary: sandbox-settings.json runs every Bash command with no network and writes only inside the checkout.

if [ "$kind" = review ]; then
  pid=$2; arm=$3; dir="$EV/runs/$pid/$arm"
  n=$(jq -r .number "$EV/prs/$pid.json")
  prompt="Review PR #$n

(Environment note: this sandbox has no internet access, but \`origin\` is a local mirror of the GitHub repository that includes pull request refs, and \`gh\` works offline against it.)"
  plugin=(); [ "$arm" != baseline ] && plugin=(--plugin-dir "$EV/plugin")
  tools="Task,Bash,Edit,Write,Read,Skill,ReportFindings,ToolSearch,TaskStop,SendMessage,ListAgents,NotebookEdit,Monitor,EnterWorktree,ExitWorktree"
  budget=10; [ "$pid" = django-17554 ] && budget=20
  stub="$EV/prs/$pid.json"
else
  mid=$2; dir="$EV/maps/$mid"
  prompt="Set up the repository maps with progressive-search (ARCHITECTURE.md and REUSE_INDEX.md). Then add a review risk map: copy the verified-code-review REVIEW_INDEX.md template to the repository root, replace the example paths with real ones, and add rows for the failure patterns that recur in this repository's history. Save the files without waiting for my confirmation."
  plugin=(--plugin-dir "$EV/plugin")
  tools="Task,Bash,Edit,Write,Read,Skill,ReportFindings,ToolSearch,TaskStop,SendMessage,ListAgents,NotebookEdit,Monitor,EnterWorktree,ExitWorktree"
  budget=15
  stub=/nonexistent
fi

cd "$dir/repo" || exit 1
start=$(date +%s)
env -i HOME="$HOME" USER="$USER" LOGNAME="$LOGNAME" SHELL=/bin/zsh LANG=en_US.UTF-8 TMPDIR="$TMPDIR" \
  PATH="$EV/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$HOME/.local/bin" \
  GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0 GH_STUB_DATA="$stub" \
  perl -e 'alarm 900; exec @ARGV' claude -p "$prompt" --model claude-sonnet-5-5 \
    --setting-sources project --strict-mcp-config --no-chrome \
    "${plugin[@]}" --tools "$tools" \
    --settings "$EV/sandbox-settings.json" --permission-mode bypassPermissions --max-budget-usd "$budget" \
    --output-format stream-json --verbose \
    < /dev/null > "$dir/run.jsonl" 2> "$dir/run.stderr"
code=$?
echo "exit=$code seconds=$(( $(date +%s) - start ))" >> "$dir/run.stderr"
echo "done: $kind ${pid:-$mid} ${arm:-} exit=$code"
