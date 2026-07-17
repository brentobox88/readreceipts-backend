import requests
import json
import os

print("📤 Testing receipt upload...")
print("=" * 40)

# Check if test_receipt.jpg exists
if not os.path.exists("test_receipt.jpg"):
    print("❌ test_receipt.jpg not found - creating one...")
    # Create a simple test image
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (800, 600), color='white')
    d = ImageDraw.Draw(img)
    d.text((50, 50), "TEST RECEIPT", fill='black')
    d.text((50, 100), "Store: Test Store", fill='black')
    d.text((50, 150), "Total: .00", fill='black')
    img.save('test_receipt.jpg')
    print("✅ Created test_receipt.jpg")

# Upload the file
try:
    with open("test_receipt.jpg", "rb") as f:
        files = {"file": ("test_receipt.jpg", f, "image/jpeg")}
        response = requests.post("http://localhost:8000/upload", files=files)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Upload successful!")
        print(f"   Receipt ID: {data.get('receipt_id')}")
        print(f"   Merchant: {data.get('data', {}).get('merchant')}")
        print(f"   Total: {data.get('data', {}).get('total')}")
        print(f"   Confidence: {data.get('data', {}).get('confidence')}")
        print(f"   Needs Review: {data.get('data', {}).get('needs_review')}")
        print(f"   Category: {data.get('data', {}).get('category')}")
    else:
        print(f"❌ Upload failed with status: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"❌ Upload error: {e}")
    print("Make sure the server is running on http://localhost:8000")
