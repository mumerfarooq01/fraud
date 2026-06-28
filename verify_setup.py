"""
Quick verification script to check if everything is set up correctly
"""
import sys
import os
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 70)
print("FRAUD DETECTION API - SETUP VERIFICATION")
print("=" * 70)

# Check 1: Configuration
print("\n1. Checking configuration...")
try:
    from app.config import settings
    print(f"   ✅ Config loaded")
    print(f"   - API Port: {settings.API_PORT}")
    print(f"   - Max File Size: {settings.MAX_FILE_SIZE_MB}MB")
    print(f"   - Gemini Configured: {bool(settings.GEMINI_API_KEY)}")
except Exception as e:
    print(f"   ❌ Error loading config: {e}")
    sys.exit(1)

# Check 2: Path to existing code
print("\n2. Checking path to existing fraud detection code...")
fraud_path = settings.FRAUD_DETECTION_CODE_PATH
if os.path.exists(fraud_path):
    print(f"   ✅ Path exists: {os.path.abspath(fraud_path)}")
else:
    print(f"   ❌ Path does not exist: {fraud_path}")
    print(f"      Update FRAUD_DETECTION_CODE_PATH in .env")

# Check 3: Can import forensics
print("\n3. Checking forensics module import...")
sys.path.insert(0, os.path.abspath(fraud_path))
try:
    from forensics import analyze_document_forensics
    print(f"   ✅ Forensics module imported successfully")
except ImportError as e:
    print(f"   ❌ Cannot import forensics: {e}")

# Check 4: Can import validators
print("\n4. Checking validators module import...")
try:
    from tax_validators.data_extractor import extract_text_from_pdf
    print(f"   ✅ Validators module imported successfully")
except ImportError as e:
    print(f"   ❌ Cannot import validators: {e}")

# Check 5: FastAPI app
print("\n5. Checking FastAPI application...")
try:
    from app.main import app
    print(f"   ✅ FastAPI app created")
    print(f"   - Title: {app.title}")
    print(f"   - Version: {app.version}")
except Exception as e:
    print(f"   ❌ Error creating app: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print("\nIf all checks passed, start the server with:")
print("  python run.py")
print("\nThen visit: http://localhost:8000/api/docs")
print("=" * 70)

