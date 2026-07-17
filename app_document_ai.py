import sys
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
from datetime import datetime
import csv
import io
import shutil
import json

# Import Document AI processor
try:
    from document_ai_service import document_ai_processor
    DOC_AI_AVAILABLE = True
    print("✅ Document AI service loaded successfully")
except ImportError as e:
    print(f"❌ Document AI not available: {e}")
    DOC_AI_AVAILABLE = False

# Initialize database
def init_db():
    conn = sqlite3.connect('receipts.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        file_path TEXT,
        upload_date TEXT,
        total_amount REAL,
        tax_amount REAL,
        net_amount REAL,
        receipt_date TEXT,
        purchase_time TEXT,
        currency TEXT,
        supplier_name TEXT,
        supplier_address TEXT,
        supplier_phone TEXT,
        confidence_score REAL,
        raw_data TEXT
    )
    ''')
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="ReadReceipts API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_receipt(file: UploadFile = File(...)):
    if not DOC_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="Document AI service not available")
    
    try:
        # Save file
        upload_dir = "uploads/receipts"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Process with Document AI
        result = document_ai_processor.process_receipt(content)
        
        if 'error' in result:
            return JSONResponse(
                status_code=400,
                content={"error": result['error']}
            )
        
        # Save to database
        conn = sqlite3.connect('receipts.db')
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO receipts (
            filename, file_path, upload_date,
            total_amount, tax_amount, net_amount,
            receipt_date, purchase_time, currency,
            supplier_name, supplier_address, supplier_phone,
            confidence_score, raw_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file.filename,
            file_path,
            datetime.now().isoformat(),
            result.get('total_amount'),
            result.get('total_tax_amount'),
            result.get('net_amount'),
            result.get('receipt_date'),
            result.get('purchase_time'),
            result.get('currency'),
            result.get('supplier_name'),
            result.get('supplier_address'),
            result.get('supplier_phone'),
            max(result.get('confidence_scores', {}).values()) if result.get('confidence_scores') else 0,
            json.dumps(result)
        ))
        conn.commit()
        conn.close()
        
        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "data": result,
            "entities_found": result.get('entities_found', []),
            "line_items_count": len(result.get('line_items', []))
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/receipts")
async def get_receipts():
    conn = sqlite3.connect('receipts.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id, filename, upload_date, total_amount, 
           supplier_name, receipt_date, currency
    FROM receipts
    ORDER BY upload_date DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    return JSONResponse(content={
        "receipts": [
            {
                "id": row[0],
                "filename": row[1],
                "upload_date": row[2],
                "total_amount": row[3],
                "supplier_name": row[4],
                "receipt_date": row[5],
                "currency": row[6]
            }
            for row in rows
        ]
    })

@app.get("/receipts/{receipt_id}")
async def get_receipt_detail(receipt_id: int):
    conn = sqlite3.connect('receipts.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    columns = ['id', 'filename', 'file_path', 'upload_date', 'total_amount', 
               'tax_amount', 'net_amount', 'receipt_date', 'purchase_time',
               'currency', 'supplier_name', 'supplier_address', 'supplier_phone',
               'confidence_score', 'raw_data']
    
    data = dict(zip(columns, row))
    data['raw_data'] = json.loads(data['raw_data']) if data['raw_data'] else {}
    
    return JSONResponse(content=data)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
