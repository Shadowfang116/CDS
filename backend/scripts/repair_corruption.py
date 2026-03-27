#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"


def replace_backtick_n(text: str) -> str:
    return text.replace("`n", "\n")


def replace_backslash_n_outside_strings(text: str) -> str:
    out = []
    i = 0
    n = len(text)
    in_str = False
    quote = ''
    triple = False
    while i < n:
        ch = text[i]
        if not in_str:
            if ch == '"' or ch == "'":
                q3 = text[i:i+3]
                if q3 in ("'''", '"""'):
                    in_str = True
                    quote = q3
                    triple = True
                    out.append(q3)
                    i += 3
                    continue
                else:
                    in_str = True
                    quote = ch
                    triple = False
                    out.append(ch)
                    i += 1
                    continue
            if ch == '\\' and (i + 1) < n and text[i + 1] == 'n':
                out.append('\n')
                i += 2
                while i < n and text[i] in (' ', '\t'):
                    out.append(text[i])
                    i += 1
                continue
            else:
                out.append(ch)
                i += 1
                continue
        else:
            if triple:
                if text[i:i+3] == quote:
                    out.append(quote)
                    i += 3
                    in_str = False
                    quote = ''
                    triple = False
                else:
                    out.append(ch)
                    i += 1
            else:
                if ch == '\\':
                    out.append(ch)
                    if i + 1 < n:
                        out.append(text[i + 1])
                        i += 2
                    else:
                        i += 1
                elif ch == quote:
                    out.append(ch)
                    i += 1
                    in_str = False
                    quote = ''
                else:
                    out.append(ch)
                    i += 1
    return ''.join(out)


def escape_newlines_inside_nontriple_strings(text: str) -> str:
    out = []
    i = 0
    n = len(text)
    in_str = False
    quote = ''
    triple = False
    while i < n:
        ch = text[i]
        if not in_str:
            if ch == '"' or ch == "'":
                q3 = text[i:i+3]
                if q3 in ("'''", '"""'):
                    in_str = True
                    quote = q3
                    triple = True
                    out.append(q3)
                    i += 3
                    continue
                else:
                    in_str = True
                    quote = ch
                    triple = False
                    out.append(ch)
                    i += 1
                    continue
            else:
                out.append(ch)
                i += 1
                continue
        else:
            if triple:
                if text[i:i+3] == quote:
                    out.append(quote)
                    i += 3
                    in_str = False
                    quote = ''
                    triple = False
                else:
                    out.append(ch)
                    i += 1
            else:
                if ch == '\n':
                    out.append('\\n')
                    i += 1
                elif ch == '\\':
                    out.append(ch)
                    if i + 1 < n:
                        out.append(text[i + 1])
                        i += 2
                    else:
                        i += 1
                elif ch == quote:
                    out.append(ch)
                    i += 1
                    in_str = False
                    quote = ''
                else:
                    out.append(ch)
                    i += 1
    return ''.join(out)


def split_glued_function_headers(text: str) -> str:
    lines = text.splitlines(True)
    new_lines = []
    for ln in lines:
        if ln.lstrip().startswith('def ') and ':' in ln:
            before, after = ln.split(':', 1)
            if after.strip():
                indent = ' ' * (len(ln) - len(ln.lstrip()))
                new_lines.append(before + ':' + '\n')
                new_lines.append(indent + '    ' + after.lstrip())
                continue
        new_lines.append(ln)
    return ''.join(new_lines)


def process_file(path: Path) -> bool:
    if path.name == 'repair_corruption.py':
        return False
    orig = path.read_text(encoding='utf-8')
    fixed = orig
    fixed = replace_backtick_n(fixed)
    fixed = replace_backslash_n_outside_strings(fixed)
    fixed = escape_newlines_inside_nontriple_strings(fixed)
    fixed = split_glued_function_headers(fixed)
    if fixed != orig:
        path.write_text(fixed, encoding='utf-8', newline='\n')
        return True
    return False


def py_compile_all(py_files):
    import py_compile
    errors = []
    for f in py_files:
        try:
            py_compile.compile(str(f), doraise=True)
        except Exception as e:
            errors.append((f, e))
    return errors


def main():
    targets = list(BACKEND_DIR.rglob('*.py'))
    changed = []
    for p in targets:
        try:
            if process_file(p):
                changed.append(p)
        except Exception as e:
            print(f"WARN: failed to process {p}: {e}")

    errors = py_compile_all(targets)
    print("=== Repair Summary ===")
    print(f"Scanned: {len(targets)} Python files")
    print(f"Modified: {len(changed)} files")
    for p in changed:
        print(f"FIXED: {p}")
    if errors:
        print("=== Syntax Errors Remaining ===")
        for f, e in errors[:50]:
            print(f"ERROR: {f}: {e}")
        return 2
    else:
        print("All files py_compile OK.")
        return 0


if __name__ == '__main__':
    raise SystemExit(main())

