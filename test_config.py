# test_config.py - Quick configuration test
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🔧 Checking environment configuration...")
print("=" * 50)

# Check required variables
required_vars = [
    ("GOOGLE_APPLICATION_CREDENTIALS", "Service account key path"),
    ("PROJECT_ID", "Google Cloud Project ID"),
    ("PROCESSOR_ID", "Document AI Processor ID"),
    ("LOCATION", "Processor region")
]

all_ok = True
missing_vars = []

for var_name, description in required_vars:
    value = os.getenv(var_name)
    if value and "your-" not in value and value.strip():
        # Show first 20 chars for security
        display_value = value[:20] + "..." if len(value) > 20 else value
        print(f"✅ {var_name}: {display_value}")
    else:
        print(f"❌ {var_name}: NOT SET or using placeholder")
        missing_vars.append((var_name, description))
        all_ok = False

print("=" * 50)

# Check if service account key file exists
key_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if key_file:
    if os.path.exists(key_file):
        print(f"✅ Service account key file found: {key_file}")
        # Check if it's a valid JSON file
        try:
            import json
            with open(key_file, 'r') as f:
                data = json.load(f)
                if 'project_id' in data and 'private_key' in data:
                    print(f"✅ Service account key appears valid")
                    print(f"   - Project ID in key: {data.get('project_id', 'N/A')}")
                else:
                    print(f"⚠️  Service account key may be invalid")
        except Exception as e:
            print(f"⚠️  Could not read service account key: {e}")
    else:
        print(f"❌ Service account key file NOT FOUND: {key_file}")
        print(f"   Please ensure the file exists in the current directory")
        all_ok = False
else:
    print(f"❌ GOOGLE_APPLICATION_CREDENTIALS not set in .env")

print("=" * 50)

# Check Python packages
print("\n📦 Checking required packages...")
required_packages = [
    'fastapi',
    'uvicorn',
    'google.cloud.documentai',
    'PIL',
    'pandas',
    'dotenv'
]

for package in required_packages:
    try:
        __import__(package.replace('.', '_'))
        print(f"✅ {package} installed")
    except ImportError:
        print(f"❌ {package} NOT installed")

print("=" * 50)

if all_ok and not missing_vars:
    print("\n🎉 Configuration looks good!")
    print("📋 Next steps:")
    print("   1. Place a test receipt image as 'test_receipt.jpg'")
    print("   2. Run: python test_ocr_integration.py")
    print("   3. Start server: python main.py")
else:
    print("\n⚠️ Missing configuration:")
    for var_name, description in missing_vars:
        print(f"   - {var_name}: {description}")
    print("\n💡 Please update your .env file with the correct values.")
    print("   If you don't have the values yet:")
    print("   1. PROJECT_ID: Get from Google Cloud Console dashboard")
    print("   2. PROCESSOR_ID: Create a processor in Document AI Console")
    print("   3. service-account-key.json: Download from Credentials section")
    sys.exit(1)

print("=" * 50)
