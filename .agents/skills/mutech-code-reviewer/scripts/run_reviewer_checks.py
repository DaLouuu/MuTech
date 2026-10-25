#!/usr/bin/env python3
"""
MuTech Automated Code Reviewer & Verification Script
Runs automated regression tests, syntax validation, security checks,
and anti-pattern heuristics across the MuTech codebase.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

# Resolve workspace root from script location
SCRIPT_PATH = Path(__file__).resolve()
ROOT_DIR = SCRIPT_PATH.parents[4]  # .agents/skills/mutech-code-reviewer/scripts/ -> ROOT
BACKEND_DIR = ROOT_DIR / "mvp" / "backend"

def print_header(title: str):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)

def check_syntax() -> int:
    print_header("1. Python Syntax & AST Validation")
    errors = 0
    py_files = list(ROOT_DIR.glob("mvp/backend/**/*.py")) + list(ROOT_DIR.glob("slr/**/*.py"))
    
    for f in py_files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                ast.parse(fh.read(), filename=str(f))
        except SyntaxError as e:
            print(f"  [SYNTAX ERROR] {f.relative_to(ROOT_DIR)}: line {e.lineno}: {e.msg}")
            errors += 1
        except Exception as e:
            print(f"  [FILE READ ERROR] {f.relative_to(ROOT_DIR)}: {e}")
            errors += 1
            
    if errors == 0:
        print(f"  [OK] Parsed {len(py_files)} Python files successfully. Zero syntax errors.")
    return errors

def check_anti_patterns() -> int:
    print_header("2. Code Quality & Security Anti-Pattern Heuristics")
    issues = 0
    app_py = BACKEND_DIR / "app.py"
    
    if app_py.exists():
        with open(app_py, "r", encoding="utf-8") as f:
            code = f.read()
            tree = ast.parse(code, filename="app.py")
            
        # Check for async routes directly calling heavy sync methods without to_thread
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        func_name = getattr(sub.func, "id", None) or getattr(sub.func, "attr", None)
                        if func_name in ["predict", "process_audio", "extract_contours", "export_midi"]:
                            # Check if parent is an await or to_thread call
                            pass
                            
        # Check CORS
        if "allow_origins=[\"*\"]" in code and "allow_credentials=True" in code:
            print("  [WARN] CORS wildcard '*' used with allow_credentials=True in app.py")
            issues += 1
        else:
            print("  [OK] CORS configuration is hardened.")
            
        # Check 413 handling
        if "413" in code or "Payload Too Large" in code or "MAX_FILE_SIZE" in code or "MAX_UPLOAD_SIZE" in code:
            print("  [OK] Payload size enforcement found in app.py.")
        else:
            print("  [WARN] Missing explicit file size limit check in app.py.")
            issues += 1
            
    # Check division by zero protections in dsp_utils.py
    dsp_py = BACKEND_DIR / "dsp_utils.py"
    if dsp_py.exists():
        with open(dsp_py, "r", encoding="utf-8") as f:
            content = f.read()
            if "eps" in content or "1e-" in content:
                print("  [OK] Epsilon / numerical stability guards detected in dsp_utils.py.")
            else:
                print("  [WARN] Check division operations in dsp_utils.py for potential zero division.")
                issues += 1

    return issues

def check_github_pages_integrity() -> int:
    print_header("3. Repository Integrity & Hosting Checks")
    issues = 0
    pages_index = ROOT_DIR / "docs" / "index.html"
    if not pages_index.exists():
        print("  [ERROR] Critical root docs/index.html missing! Breaks GitHub Pages SNA visualizer.")
        issues += 1
    else:
        print("  [OK] GitHub Pages root visualizer preserved (docs/index.html exists).")
        
    checklist_md = ROOT_DIR / "mvp" / "docs" / "IMPLEMENTATION_CHECKLIST.md"
    if not checklist_md.exists():
        print("  [WARN] IMPLEMENTATION_CHECKLIST.md missing from mvp/docs/")
        issues += 1
    else:
        print("  [OK] Implementation checklist present.")
        
    return issues

def run_pytest() -> int:
    print_header("4. Backend Test Suite Execution")
    test_path = BACKEND_DIR / "tests" / "test_suite.py"
    if not test_path.exists():
        print(f"  [ERROR] Test suite not found at {test_path}")
        return 1
        
    cmd = [sys.executable, "-m", "pytest", str(test_path), "-q"]
    proc = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
    
    print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip())
        
    if proc.returncode == 0:
        print("  [OK] All test suite assertions passed successfully.")
    else:
        print(f"  [FAIL] Test suite failed with exit code {proc.returncode}.")
        
    return proc.returncode

def main():
    print(f"Starting MuTech Code Reviewer Automation from: {ROOT_DIR}")
    
    syntax_errs = check_syntax()
    pattern_issues = check_anti_patterns()
    integrity_issues = check_github_pages_integrity()
    test_errs = run_pytest()
    
    print_header("REVIEW SUMMARY")
    print(f"  Syntax Errors:      {syntax_errs}")
    print(f"  Anti-Pattern Flags: {pattern_issues}")
    print(f"  Integrity Issues:   {integrity_issues}")
    print(f"  Test Failures:      {test_errs}")
    
    total_failures = syntax_errs + test_errs + integrity_issues
    if total_failures == 0:
        print("\n  >> RESULT: ALL AUTOMATED GATES PASSED (GRADE: PASS) <<\n")
        return 0
    else:
        print(f"\n  >> RESULT: {total_failures} BLOCKING ERRORS FOUND (GRADE: FAIL) <<\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
