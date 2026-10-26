"""Compare AST of changed .py files between a git ref and the working tree (or two refs).

Usage:
  python ast_equiv.py <base_ref> [<head_ref>] [--strip-docstrings] [files...]
If no files given, uses `git diff --name-only <base>[..<head>] -- '*.py'`.
Prints SAME / DIFF per file and a final summary. Exit 1 if any DIFF.
Comments never reach the AST, so a comment-only change must yield SAME for every file.
With --strip-docstrings, docstrings are removed on both sides before comparison, so a
comment+docstring-only change must yield SAME.
"""
import ast, subprocess, sys

def load(ref, path):
    if ref is None:
        return open(path, encoding="utf-8").read()
    return subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True, check=True).stdout

def strip_docstrings(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree

def dump(src, strip):
    tree = ast.parse(src)
    if strip:
        tree = strip_docstrings(tree)
    return ast.dump(tree, include_attributes=False)

def main():
    args = sys.argv[1:]
    strip = "--strip-docstrings" in args
    args = [a for a in args if a != "--strip-docstrings"]
    if not args:
        print(__doc__); sys.exit(2)
    base = args[0]
    head = None
    rest = args[1:]
    if rest and not rest[0].endswith(".py"):
        head = rest[0]; rest = rest[1:]
    files = rest
    if not files:
        rng = f"{base}..{head}" if head else base
        out = subprocess.run(["git", "diff", "--name-only", rng, "--", "*.py"], capture_output=True, text=True, check=True).stdout
        files = [f for f in out.split() if f.endswith(".py")]
    bad = 0
    for f in files:
        try:
            a = dump(load(base, f), strip)
        except subprocess.CalledProcessError:
            print(f"NEW   {f}"); bad += 1; continue
        try:
            b = dump(load(head, f), strip)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"GONE  {f}"); bad += 1; continue
        if a == b:
            print(f"SAME  {f}")
        else:
            print(f"DIFF  {f}"); bad += 1
    print(f"--- {len(files)} files, {bad} differ")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
