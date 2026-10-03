#!/bin/bash
# usage: run_grade.sh <pr-id>  — blind grading session for one PR (prepare it first with grade.py)
EV="$(cd "$(dirname "$0")" && pwd)"
pid=$1; dir="$EV/${GRADE_DIR:-grades}/$pid"
cd "$dir/repo" || exit 1
start=$(date +%s)
env -i HOME="$HOME" USER="$USER" LOGNAME="$LOGNAME" SHELL=/bin/zsh LANG=en_US.UTF-8 TMPDIR="$TMPDIR" \
  PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$HOME/.local/bin" GIT_ALLOW_PROTOCOL=file \
  perl -e 'alarm 1800; exec @ARGV' claude -p "$(cat "$dir/prompt.txt")" --model claude-opus-5-5 --effort high \
    --setting-sources project --strict-mcp-config --no-chrome --disable-slash-commands \
    --tools "Bash,Read" --settings "$EV/sandbox-settings.json" --permission-mode bypassPermissions \
    --max-budget-usd 15 --output-format stream-json --verbose \
    < /dev/null > "$dir/grade.jsonl" 2> "$dir/grade.stderr"
code=$?
echo "exit=$code seconds=$(( $(date +%s) - start ))" >> "$dir/grade.stderr"
echo "graded: $pid exit=$code"
