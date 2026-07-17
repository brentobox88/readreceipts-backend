import sys
import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
from datetime import datetime
import json

# Import Document AI processor
try:
    from document_ai_service import document_ai_processor
    DOC_AI_AVAILABLE = True
    print("[OK] Document AI service loaded successfully")
except ImportError as e:
    print(f"[ERROR] Document AI not available: {e}")
    DOC_AI_AVAILABLE = False

app = FastAPI(title="ReadReceipts API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "ReadReceipts API is running", "status": "healthy"}

@app.put("/receipts/{receipt_id}")
async def update_receipt(receipt_id: str, request: Request):
    try:
        data = await request.json()
        notes = data.get('notes', '')
        category = data.get('category', '')
        
        conn = sqlite3.connect('receipts.db')
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE receipts SET notes = ?, category = ?, updated_at = ? WHERE id = ?',
            (notes, category, datetime.now().isoformat(), receipt_id)
        )
        conn.commit()
        conn.close()
        
        return JSONResponse(content={"success": True, "message": "Receipt updated"})
    except Exception as e:
        print(f"Error updating receipt: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/receipts")
async def get_receipts():
    try:
        conn = sqlite3.connect('receipts.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, merchant_name, merchant_address, transaction_date, 
               total_amount, tax_amount, currency, filename, image_path,
               created_at, confidence_score, status, category
        FROM receipts
        ORDER BY created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        receipts = []
        for row in rows:
            receipts.append({
                "id": row[0],
                "merchant_name": row[1] or 'Unknown Merchant',
                "merchant_address": row[2] or '',
                "transaction_date": row[3],
                "total_amount": row[4] or 0,
                "tax_amount": row[5] or 0,
                "currency": row[6] or 'USD',
                "filename": row[7] or '',
                "image_path": row[8] or None,
                "created_at": row[9],
                "confidence_score": row[10] or 0,
                "status": row[11] or 'processed',
                "category": row[12] or None
            })
        
        return JSONResponse(content={"receipts": receipts})
    except Exception as e:
        print(f"Error in get_receipts: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/receipts/{receipt_id}")
async def get_receipt_detail(receipt_id: str):
    try:
        conn = sqlite3.connect('receipts.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        conn = sqlite3.connect('receipts.db')
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(receipts)')
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()
        
        data = dict(zip(columns, row))
        
        if data.get('line_items'):
            try:
                data['line_items'] = json.loads(data['line_items'])
            except:
                pass
        
        if data.get('parsed_data'):
            try:
                data['parsed_data'] = json.loads(data['parsed_data'])
            except:
                pass
        
        return JSONResponse(content=data)
    except Exception as e:
        print(f"Error in get_receipt_detail: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/upload")
async def upload_receipt(file: UploadFile = File(...)):
    if not DOC_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="Document AI service not available")
    
    try:
        upload_dir = "uploads/receipts"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        result = document_ai_processor.process_receipt(content)
        
        if 'error' in result:
            return JSONResponse(
                status_code=400,
                content={"error": result['error']}
            )
        
        receipt_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()
        
        merchant_name = result.get('supplier_name', 'Unknown Merchant')
        merchant_address = result.get('supplier_address', '')
        total = result.get('total_amount', 0)
        tax = result.get('total_tax_amount', 0)
        subtotal = result.get('net_amount', total - tax if tax else total)
        confidence_scores = result.get('confidence_scores', {})
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0
        line_items_json = json.dumps(result.get('line_items', []))
        parsed_data_json = json.dumps(result)
        
        conn = sqlite3.connect('receipts.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO receipts (
            id, merchant_name, merchant_address, transaction_date,
            total_amount, subtotal, tax_amount, currency,
            filename, file_path, image_path, processed_at, raw_text,
            parsed_data, confidence_score, line_items,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            receipt_id,
            merchant_name,
            merchant_address,
            result.get('receipt_date', datetime.now().isoformat()),
            total,
            subtotal,
            tax,
            result.get('currency', 'USD'),
            file.filename,
            file_path,
            file_path,
            current_time,
            result.get('raw_text', ''),
            parsed_data_json,
            avg_confidence,
            line_items_json,
            'processed',
            current_time,
            current_time
        ))
        conn.commit()
        conn.close()
        
        return JSONResponse(content={
            "success": True,
            "receipt_id": receipt_id,
            "filename": file.filename,
            "image_path": file_path,
            "data": result,
            "entities_found": result.get('entities_found', []),
            "line_items_count": len(result.get('line_items', []))
        })
        
    except Exception as e:
        print(f"Error in upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

if __name__ == "__main__":
    print("[START] Starting ReadReceipts API on 0.0.0.0:8000")
    print("[APP] Your mobile app should use: http://10.0.0.229:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
