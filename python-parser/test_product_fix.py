#!/usr/bin/env python3
"""
Quick test to check product extraction without the error.
"""
import sys
import os
sys.path.append('/Users/bogdancristianburci/Herd/InvoiceScan/python-parser')

from src.invoice_processor import InvoiceProcessor
from src.models.invoice_models import ProcessingConfig
import json

def test_product_extraction():
    """Quick test to see product extraction results."""
    
    # Test with the sample invoice
    pdf_path = '/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/public/invoice/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf'
    
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF file not found at {pdf_path}")
        return
    
    print("=== QUICK PRODUCT EXTRACTION TEST ===")
    print(f"Processing: {os.path.basename(pdf_path)}")
    print()
    
    # Create config with stream extraction 
    config = ProcessingConfig()
    config.table_extraction_flavor = "stream" 
    config.enable_ocr_validation = False
    config.validate_checksums = False
    
    processor = InvoiceProcessor(config)
    result = processor.process_invoice(pdf_path)
    
    print(f"Success: {result['success']}")
    
    if not result['success']:
        print("PROCESSING FAILED")
        return
    
    data = result.get('data', {})
    deliveries = data.get('deliveries', [])
    
    print(f"Found {len(deliveries)} deliveries")
    
    total_products = 0
    for i, delivery in enumerate(deliveries):
        products = delivery.get('products', [])
        total_products += len(products)
        print(f"Delivery {i+1} (DDT {delivery.get('ddt_number', 'N/A')}): {len(products)} products")
        
        # Show first few products safely
        for j, product in enumerate(products[:3]):
            code = product.get('product_code', 'N/A')
            qty = product.get('quantity', 'N/A')
            price = product.get('total_price', 'N/A')
            print(f"  - {code} (Qty: {qty}, Price: {price})")
    
    print(f"\nTotal products across all deliveries: {total_products}")
    
    # Save detailed results
    output_file = '/Users/bogdancristianburci/Herd/InvoiceScan/python-parser/test_results_quick.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    test_product_extraction()