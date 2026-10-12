# -*- coding: utf-8 -*-
"""一键跑测试：不依赖 pytest，右键本文件 -> Run 'run_tests' 即可。

它会把 tests/ 里所有 test_ 开头的函数逐个跑一遍，输出 PASS / FAIL。
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MODULES = ["tests.test_tools", "tests.test_core", "tests.test_langchain"]


def main():
    passed = failed = 0
    for mod_name in MODULES:
        mod = importlib.import_module(mod_name)
        for name in sorted(dir(mod)):
            if not name.startswith("test_"):
                continue
            fn = getattr(mod, name)
            try:
                fn()
                print(f"  PASS  {mod_name}.{name}")
                passed += 1
            except Exception as e:
                print(f"  FAIL  {mod_name}.{name} -> {e}")
                failed += 1
    print("-" * 50)
    print(f"结果：{passed} 通过，{failed} 失败")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
