import sys, py_compile
files = [line.strip() for line in open(sys.argv[1], 'r', encoding='utf-8') if line.strip()]
err = 0
for f in files:
    try:
        py_compile.compile(f, doraise=True)
    except Exception as e:
        print(f"ERROR: {f}: {e}")
        err = 1
sys.exit(err)
