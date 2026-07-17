# test_upload.py - Test the ReadReceipts upload endpoint
import requests
import os
import json
import sys

def test_health():
    """Test health endpoint"""
    print("📊 Testing Health Check...")
    print("=" * 40)
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Health Check Passed!")
            print(f"   Status: {data.get('status')}")
            print(f"   OCR: {data.get('ocr')}")
            print(f"   Database: {data.get('database')}")
            return True
        else:
            print(f"❌ Health Check Failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server!")
        print("   Make sure the server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Health Check Error: {e}")
        return False

def test_upload():
    """Test upload endpoint with a receipt image"""
    print("\n📤 Testing Upload...")
    print("=" * 40)
    
    # Create a test receipt image if it doesn't exist
    if not os.path.exists("test_receipt.jpg"):
        print("📸 Creating test receipt image...")
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (800, 600), color='white')
            d = ImageDraw.Draw(img)
            d.text((50, 50), "TEST RECEIPT", fill='black')
            d.text((50, 100), "Store: Test Store", fill='black')
            d.text((50, 150), "Total: .62", fill='black')
            d.text((50, 200), "Date: 2024-01-15", fill='black')
            img.save('test_receipt.jpg')
            print("✅ Created test_receipt.jpg")
        except ImportError:
            print("❌ PIL not installed. Please install: pip install Pillow")
            return False
    
    # Upload the file
    try:
        with open("test_receipt.jpg", "rb") as f:
            files = {"file": ("test_receipt.jpg", f, "image/jpeg")}
            response = requests.post("http://localhost:8000/upload", files=files, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload successful!")
            print(f"   Receipt ID: {data.get('receipt_id')}")
            receipt_data = data.get('data', {})
            print(f"   Merchant: {receipt_data.get('merchant', 'N/A')}")
            print(f"   Total: {receipt_data.get('total', 'N/A')}")
            print(f"   Confidence: {receipt_data.get('confidence', 'N/A')}")
            print(f"   Needs Review: {receipt_data.get('needs_review', 'N/A')}")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server!")
        print("   Make sure the server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def test_receipts():
    """Test get receipts endpoint"""
    print("\n📋 Testing Get Receipts...")
    print("=" * 40)
    try:
        response = requests.get("http://localhost:8000/receipts", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Get Receipts Passed!")
            print(f"   Total Receipts: {data.get('count', 0)}")
            if data.get('receipts'):
                print("   Latest Receipts:")
                for r in data['receipts'][:3]:
                    print(f"     - {r.get('merchant')}:  ({r.get('confidence', 0)*100:.0f}% confidence)")
            return True
        else:
            print(f"❌ Get Receipts Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get Receipts Error: {e}")
        return False

def test_export():
    """Test export endpoint"""
    print("\n📊 Testing Export...")
    print("=" * 40)
    try:
        response = requests.get("http://localhost:8000/export/csv", timeout=10)
        if response.status_code == 200:
            print("✅ Export successful!")
            print(f"   File size: {len(response.content)} bytes")
            # Save the CSV to see its content
            with open("test_export.csv", "wb") as f:
                f.write(response.content)
            print("   Saved as: test_export.csv")
            return True
        else:
            print(f"❌ Export failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Export Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 READRECEIPTS API TEST SUITE")
    print("=" * 60)
    print("")
    
    # Check if server is running
    print("Checking server connection...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        print("✅ Server is reachable")
    except:
        print("❌ Server is NOT reachable!")
        print("\nPlease start the server first:")
        print("  1. Open a new PowerShell window")
        print("  2. Run: python main.py")
        print("  3. Wait for it to start")
        print("  4. Run this test again")
        return
    
    print("")
    
    # Run tests
    results = []
    
    # Test 1: Health
    results.append(("Health Check", test_health()))
    
    # Test 2: Upload
    results.append(("Upload", test_upload()))
    
    # Test 3: Get Receipts
    results.append(("Get Receipts", test_receipts()))
    
    # Test 4: Export
    results.append(("Export", test_export()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}  {name}")
    
    print("-" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your backend is ready for the mobile app.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")

if __name__ == "__main__":
    main()
