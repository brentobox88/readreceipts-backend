import pandas as pd
from datetime import datetime
from typing import List, Dict
import os

class SpreadsheetExporter:
    """Exports receipts to Excel matching your spreadsheet format"""
    
    def export_to_excel(self, receipts: List[Dict], filename: str = None) -> str:
        """
        Export receipts to Excel with your column format:
        | DATE | CAD | HST | RMB | USD | NOTES |
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"receipts_export_{timestamp}.xlsx"
        
        # Ensure exports directory exists
        os.makedirs("../exports", exist_ok=True)
        filepath = f"../exports/{filename}"
        
        # Prepare data in your spreadsheet format
        data = []
        for receipt in receipts:
            # Extract values
            date = receipt.get("transaction_date", datetime.now()).strftime("%d-%b")
            total = receipt.get("total_amount", 0)
            tax = receipt.get("tax_amount", 0)
            subtotal = total - tax
            
            # Format like your spreadsheet
            row = {
                "DATE": date,
                "CAD": f"" if subtotal > 0 else "",
                "HST": f"" if tax > 0 else "",
                "RMB": "",  # Add conversion if needed
                "USD": "",  # Add conversion if needed
                "NOTES": receipt.get("notes", ""),
                "BUSINESS": receipt.get("business", "").upper(),
                "CATEGORY": receipt.get("category", "").upper(),
                "MERCHANT": receipt.get("merchant_name", "")
            }
            data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel writer
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Main sheet
            df.to_excel(writer, sheet_name='Expenses', index=False)
            
            # Summary sheet
            self._create_summary_sheet(writer, receipts)
            
            # Format columns
            worksheet = writer.sheets['Expenses']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return filepath
    
    def _create_summary_sheet(self, writer, receipts: List[Dict]):
        """Create summary sheet with totals"""
        # Calculate totals
        total_cad = sum(r.get("total_amount", 0) for r in receipts)
        total_tax = sum(r.get("tax_amount", 0) for r in receipts)
        
        # Group by business
        business_totals = {}
        for receipt in receipts:
            business = receipt.get("business", "unknown")
            if business not in business_totals:
                business_totals[business] = {"total": 0, "count": 0}
            business_totals[business]["total"] += receipt.get("total_amount", 0)
            business_totals[business]["count"] += 1
        
        # Group by category
        category_totals = {}
        for receipt in receipts:
            category = receipt.get("category", "uncategorized")
            if category not in category_totals:
                category_totals[category] = {"total": 0, "count": 0}
            category_totals[category]["total"] += receipt.get("total_amount", 0)
            category_totals[category]["count"] += 1
        
        # Create summary data
        summary_data = [
            ["TOTAL EXPENSES", f""],
            ["TOTAL TAX (HST)", f""],
            ["NET AMOUNT", f""],
            ["", ""],
            ["BUSINESS BREAKDOWN", ""]
        ]
        
        for business, data in business_totals.items():
            summary_data.append([business.upper(), f" ({data['count']} receipts)"])
        
        summary_data.append(["", ""])
        summary_data.append(["CATEGORY BREAKDOWN", ""])
        
        for category, data in category_totals.items():
            summary_data.append([category.upper(), f" ({data['count']} receipts)"])
        
        summary_df = pd.DataFrame(summary_data, columns=["Item", "Amount"])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    def export_monthly_report(self, receipts: List[Dict], month: str, year: int) -> str:
        """Export monthly report for specific business"""
        # Filter by month/year
        filtered = []
        for receipt in receipts:
            receipt_date = receipt.get("transaction_date", datetime.now())
            if receipt_date.month == month and receipt_date.year == year:
                filtered.append(receipt)
        
        filename = f"monthly_report_{year}_{month:02d}.xlsx"
        return self.export_to_excel(filtered, filename)

# Create instance
spreadsheet_exporter = SpreadsheetExporter()
