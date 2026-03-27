import importlib.util
import os
import sys

TEST_FILE = os.path.join(os.path.dirname(__file__), "test_rule_engine_mvp.py")


def load_module_from_path(path):
    spec = importlib.util.spec_from_file_location("test_mod", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def main():
    mod = load_module_from_path(TEST_FILE)
    tests = [getattr(mod, name) for name in dir(mod) if name.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL: {t.__name__}: {e}")
    if failed:
        print(f"FAILED {failed} tests")
        sys.exit(1)
    print(f"All {len(tests)} tests passed")

if __name__ == "__main__":
    main()
