# test_ocr_direct.py
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_ocr():
    print("🧪 Testing Google Document AI OCR...")
    print("=" * 50)
    
    # Check credentials
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account-key.json")
    if not os.path.exists(creds_path):
        print(f"❌ Service account key not found: {creds_path}")
        return
    
    print(f"✅ Service account key found: {creds_path}")
    
    # Check test image
    if not os.path.exists("test_receipt.jpg"):
        print("❌ test_receipt.jpg not found!")
        return
    
    print(f"✅ Test image found: test_receipt.jpg")
    
    try:
        from app.services.ocr.google_document_ai import GoogleDocumentAI
        ocr = GoogleDocumentAI()
        print("✅ OCR service initialized!")
        
        with open("test_receipt.jpg", "rb") as f:
            image_bytes = f.read()
        
        print(f"📸 Processing image ({len(image_bytes)} bytes)...")
        result = await ocr.process_receipt(image_bytes, "test_receipt.jpg")
        
        print("\n✅ OCR Results:")
        print("=" * 50)
        print(f"Merchant: {result.get('merchant_name', 'N/A')}")
        print(f"Total: {result.get('total_amount', 0)}")
        print(f"Tax: {result.get('tax_amount', 0)}")
        print(f"Date: {result.get('transaction_date', 'N/A')}")
        print(f"Category: {result.get('category', 'N/A')}")
        print(f"Confidence: {result.get('confidence', 0):.1%}")
        print(f"Line Items: {len(result.get('line_items', []))}")
        print("=" * 50)
        
        if result.get('confidence', 0) > 0.8:
            print("\n🎉 OCR is working correctly!")
        else:
            print("\n⚠️  Low confidence. Check the receipt image.")
            
    except Exception as e:
        print(f"\n❌ OCR test failed: {str(e)}")
        print("\n📋 Troubleshooting:")
        print("1. Check Google Cloud credentials")
        print("2. Verify PROCESSOR_ID in .env")
        print("3. Make sure Document AI API is enabled")

if __name__ == "__main__":
    asyncio.run(test_ocr())
