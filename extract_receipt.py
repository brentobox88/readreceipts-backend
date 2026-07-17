import sys
from google.cloud import documentai

def extract_receipt_data(document):
    receipt_data = {
        'total_amount': None,
        'total_tax_amount': None,
        'net_amount': None,
        'receipt_date': None,
        'purchase_time': None,
        'currency': None,
        'supplier_name': None,
        'supplier_address': None,
        'supplier_phone': None,
        'line_items': [],
        'confidence_scores': {}
    }
    
    for entity in document.entities:
        value = entity.normalized_value.text if hasattr(entity, 'normalized_value') and entity.normalized_value else entity.mention_text
        
        if entity.type_ == 'total_amount':
            receipt_data['total_amount'] = value
            receipt_data['confidence_scores']['total_amount'] = entity.confidence
        elif entity.type_ == 'total_tax_amount':
            receipt_data['total_tax_amount'] = value
            receipt_data['confidence_scores']['total_tax_amount'] = entity.confidence
        elif entity.type_ == 'net_amount':
            receipt_data['net_amount'] = value
            receipt_data['confidence_scores']['net_amount'] = entity.confidence
        elif entity.type_ == 'receipt_date':
            receipt_data['receipt_date'] = value
            receipt_data['confidence_scores']['receipt_date'] = entity.confidence
        elif entity.type_ == 'purchase_time':
            receipt_data['purchase_time'] = value
            receipt_data['confidence_scores']['purchase_time'] = entity.confidence
        elif entity.type_ == 'currency':
            receipt_data['currency'] = value
            receipt_data['confidence_scores']['currency'] = entity.confidence
        elif entity.type_ == 'supplier_name':
            receipt_data['supplier_name'] = value
            receipt_data['confidence_scores']['supplier_name'] = entity.confidence
        elif entity.type_ == 'supplier_address':
            receipt_data['supplier_address'] = value
            receipt_data['confidence_scores']['supplier_address'] = entity.confidence
        elif entity.type_ == 'supplier_phone':
            receipt_data['supplier_phone'] = value
            receipt_data['confidence_scores']['supplier_phone'] = entity.confidence
        elif entity.type_.startswith('line_item/'):
            # Extract line item
            item = {}
            for prop in entity.properties:
                prop_value = prop.mention_text
                if prop.type_ == 'line_item/description':
                    item['description'] = prop_value
                elif prop.type_ == 'line_item/quantity':
                    item['quantity'] = prop_value
                elif prop.type_ == 'line_item/unit_price':
                    item['unit_price'] = prop_value
                elif prop.type_ == 'line_item/amount':
                    item['amount'] = prop_value
            if item:
                receipt_data['line_items'].append(item)
    
    return receipt_data

# Example usage (replace with your actual processing)
print("Extraction function ready!")
print("Add your Document AI processing code here")
