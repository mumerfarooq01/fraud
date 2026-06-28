"""
Phase 1 Completion Checklist
Verify all required files and structure are in place
"""
import os
import sys

def check_file(path, description):
    """Check if a file exists"""
    exists = os.path.exists(path)
    status = "+" if exists else "-"
    print(f"  {status} {description}")
    return exists

def check_dir(path, description):
    """Check if a directory exists"""
    exists = os.path.isdir(path)
    status = "+" if exists else "-"
    print(f"  {status} {description}")
    return exists

print("=" * 70)
print("PHASE 1 COMPLETION VERIFICATION")
print("=" * 70)

all_good = True

# 1. Root Level Files
print("\n[1] ROOT LEVEL FILES:")
all_good &= check_file(".env", ".env (environment config)")
all_good &= check_file(".gitignore", ".gitignore")
all_good &= check_file("requirements.txt", "requirements.txt")
all_good &= check_file("run.py", "run.py (server launcher)")
all_good &= check_file("README.md", "README.md (full docs)")
all_good &= check_file("QUICKSTART.md", "QUICKSTART.md (quick guide)")
all_good &= check_file("verify_setup.py", "verify_setup.py")
all_good &= check_file("phase1_checklist.py", "phase1_checklist.py (this file)")

# 2. Directory Structure
print("\n[2] DIRECTORY STRUCTURE:")
all_good &= check_dir("app", "app/")
all_good &= check_dir("app/api", "app/api/")
all_good &= check_dir("app/api/v1", "app/api/v1/")
all_good &= check_dir("app/api/v1/routes", "app/api/v1/routes/")
all_good &= check_dir("app/api/v1/schemas", "app/api/v1/schemas/")
all_good &= check_dir("tests", "tests/")

# 3. Core Application Files
print("\n[3] CORE APPLICATION FILES:")
all_good &= check_file("app/__init__.py", "app/__init__.py")
all_good &= check_file("app/main.py", "app/main.py (FastAPI app)")
all_good &= check_file("app/config.py", "app/config.py (settings)")

# 4. API Package Files
print("\n[4] API PACKAGE FILES:")
all_good &= check_file("app/api/__init__.py", "app/api/__init__.py")
all_good &= check_file("app/api/v1/__init__.py", "app/api/v1/__init__.py")

# 5. API Routes
print("\n[5] API ROUTES:")
all_good &= check_file("app/api/v1/routes/__init__.py", "routes/__init__.py")
all_good &= check_file("app/api/v1/routes/forensics.py", "routes/forensics.py")
all_good &= check_file("app/api/v1/routes/comparison.py", "routes/comparison.py")
all_good &= check_file("app/api/v1/routes/database.py", "routes/database.py")

# 6. API Schemas
print("\n[6] API SCHEMAS:")
all_good &= check_file("app/api/v1/schemas/__init__.py", "schemas/__init__.py")
all_good &= check_file("app/api/v1/schemas/forensics.py", "schemas/forensics.py")
all_good &= check_file("app/api/v1/schemas/comparison.py", "schemas/comparison.py")

# 7. Tests
print("\n[7] TESTS:")
all_good &= check_file("tests/__init__.py", "tests/__init__.py")
all_good &= check_file("tests/test_api.py", "tests/test_api.py")

# 8. File Counts
print("\n[8] FILE COUNTS:")
total_files = sum([len(files) for r, d, files in os.walk(".")])
py_files = sum([len([f for f in files if f.endswith('.py')]) for r, d, files in os.walk(".")])
print(f"  Total files: {total_files}")
print(f"  Python files: {py_files}")

# 9. Dependencies Check
print("\n[9] DEPENDENCIES:")
try:
    import fastapi
    print(f"  + FastAPI {fastapi.__version__} installed")
except ImportError:
    print("  - FastAPI NOT installed")
    all_good = False

try:
    import uvicorn
    print(f"  + Uvicorn installed")
except ImportError:
    print("  - Uvicorn NOT installed")
    all_good = False

try:
    import pydantic
    print(f"  + Pydantic {pydantic.__version__} installed")
except ImportError:
    print("  - Pydantic NOT installed")
    all_good = False

# 10. Configuration Check
print("\n[10] CONFIGURATION:")
if os.path.exists(".env"):
    with open(".env", "r") as f:
        env_content = f.read()
        has_gemini = "GEMINI_API_KEY=" in env_content
        has_port = "API_PORT=" in env_content
        has_path = "FRAUD_DETECTION_CODE_PATH=" in env_content
        
        print(f"  {'+' if has_gemini else '-'} GEMINI_API_KEY configured")
        print(f"  {'+' if has_port else '-'} API_PORT configured")
        print(f"  {'+' if has_path else '-'} FRAUD_DETECTION_CODE_PATH configured")
        
        all_good &= has_gemini and has_port and has_path

# Summary
print("\n" + "=" * 70)
if all_good:
    print("[SUCCESS] PHASE 1 COMPLETE - ALL CHECKS PASSED!")
    print("=" * 70)
    print("\nYou can now start the server:")
    print("  cd C:\\Users\\qaboo\\source\\repos\\fraud-detection-api")
    print("  python run.py")
    print("\nThen visit: http://localhost:8000/api/docs")
else:
    print("[WARNING] PHASE 1 INCOMPLETE - Some items are missing")
    print("=" * 70)
    sys.exit(1)

