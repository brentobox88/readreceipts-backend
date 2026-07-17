# test_upload_simple.py - Simple upload test
import requests
import json
import os

def test_upload():
    print("📤 Testing upload...")
    print("=" * 40)
    
    # Create a test image if needed
    if not os.path.exists("test_receipt.jpg"):
        print("📸 Creating test receipt image...")
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (800, 600), color='white')
            d = ImageDraw.Draw(img)
            d.text((50, 50), "STARBUCKS COFFEE", fill='black')
            d.text((50, 100), "123 Main Street", fill='black')
            d.text((50, 150), "Total: .62", fill='black')
            d.text((50, 200), "Date: 2024-01-15", fill='black')
            img.save('test_receipt.jpg')
            print("✅ Created test_receipt.jpg")
        except Exception as e:
            print(f"❌ Could not create test image: {e}")
            return False
    
    # Upload the file
    try:
        with open("test_receipt.jpg", "rb") as f:
            files = {"file": ("test_receipt.jpg", f, "image/jpeg")}
            response = requests.post("http://localhost:8000/upload", files=files, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload successful!")
            print(f"   Receipt ID: {data.get('receipt_id')}")
            receipt_data = data.get('data', {})
            print(f"   Merchant: {receipt_data.get('merchant', 'N/A')}")
            print(f"   Total: {receipt_data.get('total', 'N/A')}")
            print(f"   Confidence: {receipt_data.get('confidence', 'N/A')}")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def test_health():
    print("\n📊 Testing health...")
    print("=" * 40)
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed!")
            print(f"   Status: {data.get('status')}")
            print(f"   OCR: {data.get('ocr')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 SIMPLE API TEST")
    print("=" * 60)
    print("")
    
    # Check server
    print("Checking server connection...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        print("✅ Server is reachable")
    except:
        print("❌ Server is NOT reachable!")
        print("   Start server: python main.py")
        exit()
    
    print("")
    
    # Run tests
    health_ok = test_health()
    upload_ok = test_upload()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Health: {'✅ PASSED' if health_ok else '❌ FAILED'}")
    print(f"Upload: {'✅ PASSED' if upload_ok else '❌ FAILED'}")
    
    if health_ok and upload_ok:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
