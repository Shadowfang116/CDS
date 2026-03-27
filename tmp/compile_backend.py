import os, sys, py_compile
base = os.path.join(r"'+$repo+'", "backend")
errors = []
for root, _, files in os.walk(base):
    for fn in files:
        if fn.endswith('.py'):
            p = os.path.join(root, fn)
            try:
                py_compile.compile(p, doraise=True)
            except Exception as e:
                errors.append((p, e))

if errors:
    print("PY_COMPILE_ERRORS:")
    for p, e in errors:
        try:
            pe = str(p)
        except Exception:
            pe = repr(p)
        try:
            ee = str(e)
        except Exception:
            ee = repr(e)
        print(f"- {pe}: {ee}")
    sys.exit(1)
else:
    print("PY_COMPILE_OK")
    sys.exit(0)
