#!/usr/bin/env python3
"""List what a diff changed and where it is used, as a starting map for tracing.

Usage: python3 changed_symbols.py BASE HEAD [--max-callers N]

Reads git objects only (never the working tree), so it is safe on any checkout.
For each changed function or class: the commit it changed in, its callers at HEAD
(outside its own definition), and other definitions with the same name (overrides).
Also lists calls the diff removed and attributes it added, two common sources of
regressions. Python files are parsed with `ast`; other files fall back to git's
hunk-header function context.
"""
import ast
import re
import subprocess
import sys
from collections import defaultdict

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)$")
CALL = re.compile(r"(?:\.|\b)([A-Za-z_][A-Za-z0-9_]*)\s*\(")
ATTR = re.compile(r"\bself\.([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=(?!=)")
SKIP = re.compile(r"(^|/)(tests?|testing|docs?|docs_src|examples?)/|(^|/)test_[^/]*$|_test\.[a-z]+$|\.(md|rst|txt|json|ya?ml|toml|cfg|ini|html|css|po|lock)$")
KEYWORDS = {"and", "or", "not", "in", "is", "lambda", "assert", "yield", "await", "raise", "elif", "with", "except", "if", "for", "while", "return", "print", "len", "isinstance", "super", "str", "int",
            "list", "dict", "set", "tuple", "getattr", "hasattr", "setattr", "range", "type", "bool"}


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def parse_diff(base, head):
    """Yield (path, old_ranges, new_ranges, removed_lines, added_lines, header_contexts)."""
    files = defaultdict(lambda: {"old": [], "new": [], "removed": [], "added": [], "ctx": set()})
    path = None
    for line in git("diff", "-U0", "--no-color", "--no-renames", f"{base}...{head}").splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("--- "):
            if line.startswith("--- a/") and path is None:
                pass
        elif path and (m := HUNK.match(line)):
            o, oc, n, nc, ctx = m.groups()
            oc, nc = int(oc or 1), int(nc or 1)
            f = files[path]
            if oc:
                f["old"].append((int(o), int(o) + oc - 1))
            if nc:
                f["new"].append((int(n), int(n) + nc - 1))
            if ctx.strip():
                f["ctx"].add(ctx.strip())
        elif path and line.startswith("-") and not line.startswith("---"):
            files[path]["removed"].append(line[1:])
        elif path and line.startswith("+") and not line.startswith("+++"):
            files[path]["added"].append(line[1:])
    return files


def enclosing(source, ranges):
    """Qualified names (Class.method or function) of the outermost callable around each range.

    A nested helper is reported as its enclosing function, since callers reach it through that.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    units = []  # (start, end, qualname)

    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, prefix + [child.name])
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = min([child.lineno] + [d.lineno for d in child.decorator_list])
                units.append((start, child.end_lineno, ".".join(prefix + [child.name])))
    walk(tree, [])
    classes = [(n.lineno, n.end_lineno, n.name) for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    found = set()
    for lo, hi in ranges:
        hit = [u for u in units if u[0] <= hi and u[1] >= lo]
        if not hit:
            hit = [c for c in classes if c[0] <= hi and c[1] >= lo][-1:]
        found.update(u[2] for u in hit)
    return found


def header_name(ctx):
    m = re.search(r"(?:def|class|func|function|fn)\s+([A-Za-z_][A-Za-z0-9_]*)", ctx) or re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(", ctx)
    return m.group(1) if m else None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    base, head = args
    max_callers = 12
    if "--max-callers" in sys.argv:
        max_callers = int(sys.argv[sys.argv.index("--max-callers") + 1])

    files = parse_diff(base, head)
    symbols = defaultdict(set)  # name -> files where it changed
    removed_calls, new_attrs = defaultdict(set), defaultdict(set)
    for path, f in files.items():
        if SKIP.search(path):
            continue
        names = set()
        if path.endswith(".py"):
            names |= enclosing(git("show", f"{head}:{path}"), f["new"])
            names |= enclosing(git("show", f"{base}:{path}"), f["old"])
        if not names:
            names = {n for n in map(header_name, f["ctx"]) if n}
        for n in names:
            symbols[n].add(path)
        added_text = "\n".join(f["added"])
        for line in f["removed"]:
            for c in CALL.findall(line):
                if c not in KEYWORDS and not re.search(rf"\b{re.escape(c)}\s*\(", added_text):
                    removed_calls[path].add(c)
        base_src = git("show", f"{base}:{path}")
        for line in f["added"]:
            for a in ATTR.findall(line):
                if f"self.{a}" not in base_src:
                    new_attrs[path].add(a)

    print(f"# Change map {base[:10]}...{head[:10]}\n")
    print(f"Changed files: {len(files)}\n")
    print("## Changed functions and classes, with callers at HEAD\n")
    def search_name(qual):
        parts = qual.split(".")
        leaf = parts[-1]
        if (leaf.startswith("__") or leaf in ("Meta", "app", "main", "run", "get", "set")) and len(parts) > 1:
            return parts[-2]
        return leaf

    for qual in sorted(symbols):
        name = search_name(qual)
        hits = [h.split(":", 1)[1] for h in git("grep", "-n", "-w", "-e", name, head, "--").splitlines()]
        hits = [h for h in hits if not re.search(r"\.(md|rst|txt|po|html)$", h.split(":", 1)[0])]
        defs = [h for h in hits if re.search(rf"\b(def|class|function|func)\s+{re.escape(name)}\b", h)]
        uses = [h for h in hits if h not in defs]
        src_uses = [h for h in uses if not SKIP.search(h.split(":", 1)[0])]
        shown = f"`{qual}`" + (f" (searched as `{name}`)" if name != qual.split(".")[-1] else "")
        print(f"### {shown} in {', '.join(sorted(symbols[qual]))}")
        print(f"Definitions named `{name}`: {len(defs)}" + (" (several: check overrides, subclasses and same-named twins)" if len(defs) > 1 else ""))
        for d in defs[:6]:
            print(f"  def  {d[:160]}")
        print(f"Uses outside tests and docs: {len(src_uses)}; in tests: {len(uses) - len(src_uses)}")
        for u in src_uses[:max_callers]:
            print(f"  use  {u[:160]}")
        if len(src_uses) > max_callers:
            print(f"  ... {len(src_uses) - max_callers} more: git grep -n -w -e {name} {head[:10]} -- ':!tests'")
        print()
    if removed_calls:
        print("## Calls removed by the diff (check each side effect still happens)\n")
        for path, calls in sorted(removed_calls.items()):
            print(f"- {path}: {', '.join(sorted(calls))}")
        print()
    if new_attrs:
        print("## Attributes added (check every place these objects are built, copied or rebuilt)\n")
        for path, attrs in sorted(new_attrs.items()):
            print(f"- {path}: {', '.join(sorted(attrs))}")
        print()


if __name__ == "__main__":
    main()
