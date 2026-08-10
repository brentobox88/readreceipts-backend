import sys
import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse, Response

# ============================================
# GUARANTEED DATABASE INITIALIZATION
# ============================================
import sqlite3
conn = sqlite3.connect('/opt/render/project/src/data/receipts.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS receipts (
    id TEXT PRIMARY KEY,
    merchant_name TEXT,
    merchant_address TEXT,
    transaction_date TEXT,
    total_amount REAL,
    subtotal REAL,
    tax_amount REAL,
    currency TEXT,
    filename TEXT,
    file_path TEXT,
    image_path TEXT,
    processed_at TEXT,
    raw_text TEXT,
    parsed_data TEXT,
    confidence_score REAL,
    line_items TEXT,
    document_type TEXT,
    document_number TEXT,
    client_name TEXT,
    client_address TEXT,
    due_date TEXT,
    tax_year TEXT,
    tax_type TEXT,
    payment_method TEXT,
    is_business INTEGER,
    is_reimbursable INTEGER,
    income_amount REAL,
    expense_amount REAL,
    tax_amount_paid REAL,
    category TEXT,
    status TEXT,
    notes TEXT,
    created_at TEXT,
    updated_at TEXT
);
''')
conn.commit()
conn.close()
print("[DB] Database initialized successfully!")
# ============================================
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
from datetime import datetime
import json

# ============================================
# GUARANTEED DATABASE INITIALIZATION
# ============================================
import sqlite3
conn = sqlite3.connect('/opt/render/project/src/data/receipts.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS receipts (
    id TEXT PRIMARY KEY,
    merchant_name TEXT,
    merchant_address TEXT,
    transaction_date TEXT,
    total_amount REAL,
    subtotal REAL,
    tax_amount REAL,
    currency TEXT,
    filename TEXT,
    file_path TEXT,
    image_path TEXT,
    processed_at TEXT,
    raw_text TEXT,
    parsed_data TEXT,
    confidence_score REAL,
    line_items TEXT,
    document_type TEXT,
    document_number TEXT,
    client_name TEXT,
    client_address TEXT,
    due_date TEXT,
    tax_year TEXT,
    tax_type TEXT,
    payment_method TEXT,
    is_business INTEGER,
    is_reimbursable INTEGER,
    income_amount REAL,
    expense_amount REAL,
    tax_amount_paid REAL,
    category TEXT,
    status TEXT,
    notes TEXT,
    created_at TEXT,
    updated_at TEXT
);
''')
conn.commit()
conn.close()
print("[DB] Database initialized successfully!")
# ============================================

# ============================================
# HARDCODED VALUES - For demo deployment
# ============================================
PROJECT_ID = "receipt-relief"
PROCESSOR_ID = "896553633cd26552"
# ============================================

# Import Document AI processor
from document_ai_service import document_ai_processor

DOC_AI_AVAILABLE = True

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

@app.get("/debug")
def debug():
    return {
        "PROJECT_ID": PROJECT_ID,
        "PROCESSOR_ID": PROCESSOR_ID,
        "status": "hardcoded"
    }

@app.put("/receipts/{receipt_id}")
async def update_receipt(receipt_id: str, request: Request):
    try:
        data = await request.json()
        
        # Define all fields that can be updated
        updateable_fields = [
            "merchant_name", "merchant_address", "transaction_date",
            "total_amount", "tax_amount", "currency",
            "document_type", "document_number", "client_name",
            "due_date", "tax_type", "tax_year",
            "income_amount", "expense_amount", "tax_amount_paid",
            "category", "notes", "status"
        ]
        
        # Build the SET clause dynamically
        set_clauses = []
        values = []
        for field in updateable_fields:
            if field in data:
                set_clauses.append(f"{field} = ?")
                values.append(data[field])
        
        if not set_clauses:
            return JSONResponse(
                status_code=400,
                content={"error": "No valid fields to update"}
            )
        
        # Add updated_at timestamp
        set_clauses.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(receipt_id)
        
        query = f"UPDATE receipts SET {', '.join(set_clauses)} WHERE id = ?"
        
        conn = sqlite3.connect('/opt/render/project/src/data/receipts.db')
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        
        return JSONResponse(content={"success": True, "message": "Receipt updated"})
    except Exception as e:
        print(f"Error updating receipt: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )(content={"success": True, "message": "Receipt updated"})
    except Exception as e:
        print(f"Error updating receipt: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/receipts")
async def get_receipts():
    try:
        conn = sqlite3.connect('/opt/render/project/src/data/receipts.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, merchant_name, merchant_address, transaction_date, 
               total_amount, tax_amount, currency, filename, image_path,
               created_at, confidence_score, status, category,
               document_type, document_number, client_name, 
               income_amount, expense_amount, tax_amount_paid
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
                "category": row[12] or None,
                "document_type": row[13] or 'expense',
                "document_number": row[14] or None,
                "client_name": row[15] or None,
                "income_amount": row[16] or 0,
                "expense_amount": row[17] or 0,
                "tax_amount_paid": row[18] or 0
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
        conn = sqlite3.connect('/opt/render/project/src/data/receipts.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        conn = sqlite3.connect('/opt/render/project/src/data/receipts.db')
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
    try:
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
        
        # Determine classification
        raw_text = result.get('raw_text', '')
        classification = {
            'document_type': 'expense',
            'category': 'Uncategorized',
            'is_business': 1,
            'is_reimbursable': 0
        }
        if 'invoice' in raw_text.lower() or 'tax invoice' in raw_text.lower():
            classification['document_type'] = 'invoice'
        if 'tax' in raw_text.lower() or 'gst' in raw_text.lower() or 'vat' in raw_text.lower():
            classification['document_type'] = 'tax'
        
        # Determine amounts based on document type
        if classification['document_type'] == 'invoice':
            income_amount = total
            expense_amount = 0
        else:
            income_amount = 0
            expense_amount = total
        
        tax_paid = 0
        if classification['document_type'] == 'tax':
            tax_paid = total
        
        conn = sqlite3.connect('/opt/render/project/src/data/receipts.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO receipts (
            id, merchant_name, merchant_address, transaction_date,
            total_amount, subtotal, tax_amount, currency,
            filename, file_path, image_path, processed_at, raw_text,
            parsed_data, confidence_score, line_items,
            document_type, document_number, client_name, client_address,
            due_date, tax_year, tax_type, payment_method,
            is_business, is_reimbursable,
            income_amount, expense_amount, tax_amount_paid,
            category, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            raw_text,
            parsed_data_json,
            avg_confidence,
            line_items_json,
            classification.get('document_type', 'expense'),
            classification.get('document_number', ''),
            classification.get('client_name', ''),
            classification.get('client_address', ''),
            classification.get('due_date', ''),
            classification.get('tax_year', ''),
            classification.get('tax_type', ''),
            '',
            classification.get('is_business', 1),
            classification.get('is_reimbursable', 0),
            income_amount,
            expense_amount,
            tax_paid,
            classification.get('category', 'Uncategorized'),
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
            "classification": classification,
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

@app.post("/reports/generate")
async def generate_report(request: Request):
    try:
        filters = await request.json()
        
        conn = sqlite3.connect('/opt/render/project/src/data/receipts.db')
        cursor = conn.cursor()
        
        # Build query based on filters
        query = 'SELECT * FROM receipts WHERE 1=1'
        params = []
        
        if filters.get('startDate'):
            query += ' AND transaction_date >= ?'
            params.append(filters['startDate'])
        
        if filters.get('endDate'):
            query += ' AND transaction_date <= ?'
            params.append(filters['endDate'])
        
        if filters.get('document_type') and filters['document_type'] != 'all':
            query += ' AND document_type = ?'
            params.append(filters['document_type'])
        
        if filters.get('category'):
            query += ' AND category = ?'
            params.append(filters['category'])
        
        if filters.get('minAmount'):
            query += ' AND total_amount >= ?'
            params.append(filters['minAmount'])
        
        if filters.get('maxAmount'):
            query += ' AND total_amount <= ?'
            params.append(filters['maxAmount'])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Get column names
        cursor.execute('PRAGMA table_info(receipts)')
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()
        
        receipts = []
        for row in rows:
            data = dict(zip(columns, row))
            if data.get('line_items'):
                try:
                    data['line_items'] = json.loads(data['line_items'])
                except:
                    pass
            receipts.append(data)
        
        # Generate summary
        summary = {
            'total_receipts': len(receipts),
            'total_income': sum(r.get('income_amount', 0) or r.get('total_amount', 0) for r in receipts if r.get('document_type') == 'invoice'),
            'total_expenses': sum(r.get('expense_amount', 0) or r.get('total_amount', 0) for r in receipts if r.get('document_type') == 'expense'),
            'total_tax': sum(r.get('tax_amount_paid', 0) for r in receipts if r.get('document_type') == 'tax'),
            'net_income': sum(r.get('income_amount', 0) or r.get('total_amount', 0) for r in receipts if r.get('document_type') == 'invoice') - 
                         sum(r.get('expense_amount', 0) or r.get('total_amount', 0) for r in receipts if r.get('document_type') == 'expense')
        }
        
        # Category breakdown
        categories = {}
        for r in receipts:
            cat = r.get('category') or 'Uncategorized'
            categories[cat] = categories.get(cat, 0) + (r.get('total_amount', 0))
        
        # Document type breakdown
        doc_types = {}
        for r in receipts:
            doc_type = r.get('document_type') or 'expense'
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        return JSONResponse(content={
            'summary': summary,
            'breakdown': {
                'by_category': categories,
                'by_document_type': doc_types
            },
            'receipts': receipts
        })
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/export")
async def export_receipts():
    try:
        import io
        import csv
        conn = sqlite3.connect('/opt/render/project/src/data/receipts.db')
        cursor = conn.cursor()
        cursor.execute('''
        SELECT 
            merchant_name, 
            transaction_date, 
            total_amount, 
            currency,
            document_type,
            document_number,
            client_name,
            due_date,
            tax_type,
            tax_year,
            income_amount,
            expense_amount,
            tax_amount_paid,
            category,
            confidence_score,
            status
        FROM receipts
        ORDER BY created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Merchant', 'Date', 'Amount', 'Currency',
            'Document Type', 'Document #', 'Client Name', 'Due Date',
            'Tax Type', 'Tax Year', 'Income', 'Expense', 'Tax Paid',
            'Category', 'Confidence', 'Status'
        ])
        
        for row in rows:
            writer.writerow([
                row[0] or 'Unknown',
                row[1] or 'N/A',
                row[2] or 0,
                row[3] or 'USD',
                row[4] or 'expense',
                row[5] or '',
                row[6] or '',
                row[7] or '',
                row[8] or '',
                row[9] or '',
                row[10] or 0,
                row[11] or 0,
                row[12] or 0,
                row[13] or 'Uncategorized',
                f"{row[14] or 0:.0f}%",
                row[15] or 'processed'
            ])
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=receipts_export.csv"}
        )
    except Exception as e:
        print(f"Error exporting: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

if __name__ == '__main__':
    print("[START] Starting ReadReceipts API on 0.0.0.0:8000")
    print("[APP] Your mobile app should use: http://10.0.0.229:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)





