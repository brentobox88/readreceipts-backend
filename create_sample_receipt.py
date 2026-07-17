# sample_receipt.py - Creates a sample receipt image for testing
from PIL import Image, ImageDraw, ImageFont
import os

def create_sample_receipt():
    # Create a blank white image
    img = Image.new('RGB', (800, 600), color='white')
    d = ImageDraw.Draw(img)
    
    # Try to use a font, fall back to default
    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_normal = ImageFont.truetype("arial.ttf", 16)
    except:
        font_title = ImageFont.load_default()
        font_normal = ImageFont.load_default()
    
    # Draw a simple receipt
    y = 30
    d.text((50, y), "STARBUCKS", fill='black', font=font_title)
    y += 40
    d.text((50, y), "123 Main Street", fill='black', font=font_normal)
    y += 25
    d.text((50, y), "New York, NY 10001", fill='black', font=font_normal)
    y += 25
    d.text((50, y), "Tel: (555) 123-4567", fill='black', font=font_normal)
    
    y += 40
    d.line([(50, y), (750, y)], fill='black', width=1)
    y += 20
    
    # Add items
    items = [
        ("Cafe Latte", "1", ".50"),
        ("Blueberry Muffin", "1", ".25"),
        ("Bottled Water", "2", ".00"),
    ]
    
    for item, qty, price in items:
        d.text((50, y), item, fill='black', font=font_normal)
        d.text((600, y), qty, fill='black', font=font_normal)
        d.text((700, y), price, fill='black', font=font_normal)
        y += 25
    
    y += 10
    d.line([(50, y), (750, y)], fill='black', width=1)
    y += 20
    
    d.text((50, y), "Subtotal:", fill='black', font=font_normal)
    d.text((700, y), ".75", fill='black', font=font_normal)
    y += 25
    d.text((50, y), "Tax (8.875%):", fill='black', font=font_normal)
    d.text((700, y), ".87", fill='black', font=font_normal)
    y += 25
    d.text((50, y), "Total:", fill='black', font=font_title)
    d.text((700, y), ".62", fill='black', font=font_title)
    
    y += 40
    d.line([(50, y), (750, y)], fill='black', width=1)
    y += 20
    d.text((50, y), "Payment: Mastercard ****1234", fill='black', font=font_normal)
    y += 25
    d.text((50, y), "Date: 2024-01-15 10:30 AM", fill='black', font=font_normal)
    y += 25
    d.text((50, y), "Receipt #: 123456", fill='black', font=font_normal)
    
    # Save the image
    img.save('test_receipt.jpg')
    print("✅ Created test_receipt.jpg in the current directory")

if __name__ == "__main__":
    create_sample_receipt()
