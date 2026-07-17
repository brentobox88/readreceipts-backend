# test_ocr_integration.py
# Test script to verify OCR integration

import asyncio
import os
import base64
from dotenv import load_dotenv
from app.services.ocr.google_document_ai import GoogleDocumentAI

# Load environment variables
load_dotenv()

async def test_ocr():
    """Test OCR with a sample image"""
    print("🧪 Testing OCR Integration...")
    print("=" * 50)
    
    # Check if credentials exist
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set!")
        print("   Set it to the path of your service account key JSON file")
        return
    
    # Check for test image
    test_image_path = "test_receipt.jpg"
    if not os.path.exists(test_image_path):
        print(f"⚠️  No test image found at: {test_image_path}")
        print("   Please add a test receipt image named 'test_receipt.jpg'")
        return
    
    print(f"📸 Using test image: {test_image_path}")
    
    try:
        # Read image
        with open(test_image_path, "rb") as f:
            image_bytes = f.read()
        
        print("📤 Sending image to OCR service...")
        
        # Initialize OCR service
        ocr = GoogleDocumentAI()
        
        # Process
        result = await ocr.process_receipt(image_bytes, "test_receipt.jpg")
        
        print("\n✅ OCR Results:")
        print("=" * 50)
        print(f"Merchant: {result.get('merchant_name', 'N/A')}")
        print(f"Total: {result.get('total_amount', 0)}")
        print(f"Date: {result.get('transaction_date', 'N/A')}")
        print(f"Tax: {result.get('tax_amount', 0)}")
        print(f"Category: {result.get('category', 'N/A')}")
        print(f"Confidence: {result.get('confidence', 0):.1%}")
        print(f"Line Items: {len(result.get('line_items', []))}")
        print("=" * 50)
        
        # Show field confidence
        print("\n📊 Field Confidence:")
        for field, confidence in result.get('field_confidences', {}).items():
            if confidence:
                status = "✅" if confidence > 0.85 else "⚠️"
                print(f"  {status} {field}: {confidence:.1%}")
        
        print("\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        print("\nPossible issues:")
        print("1. Invalid API credentials")
        print("2. Missing processor ID")
        print("3. Network connectivity")
        print("4. Image format not supported")

if __name__ == "__main__":
    asyncio.run(test_ocr())
