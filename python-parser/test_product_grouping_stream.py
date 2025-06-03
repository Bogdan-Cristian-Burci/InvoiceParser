#!/usr/bin/env python3
"""
Test script to verify product grouping per delivery functionality using stream extraction.
"""
import sys
import os
sys.path.append('/Users/bogdancristianburci/Herd/InvoiceScan/python-parser')

from src.invoice_processor import InvoiceProcessor
from src.models.invoice_models import ProcessingConfig
import json

def test_product_grouping():
    """Test the product grouping functionality with the sample invoice."""
    
    # Test with the sample invoice
    pdf_path = '/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/public/invoice/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf'
    
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF file not found at {pdf_path}")
        return
    
    print("=== TESTING PRODUCT GROUPING PER DELIVERY (STREAM MODE) ===")
    print(f"Processing: {os.path.basename(pdf_path)}")
    print()
    
    # Create config with stream extraction (doesn't require Ghostscript)
    config = ProcessingConfig()
    config.table_extraction_flavor = "stream"  # Use stream instead of lattice
    config.enable_ocr_validation = False  # Disable OCR for this test
    config.validate_checksums = False  # Disable checksum validation for this test
    
    processor = InvoiceProcessor(config)
    result = processor.process_invoice(pdf_path)
    
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print()
    
    if not result['success']:
        print("=== PROCESSING FAILED ===")
        if 'data' in result and 'parsing_errors' in result['data']:
            for error in result['data']['parsing_errors']:
                print(f"  ERROR: {error}")
        return
    
    data = result.get('data', {})
    
    # Test Bill Information
    print("=== BILL INFORMATION ===")
    bill = data.get('bill', {})
    print(f"Bill Number: {bill.get('bill_number', 'N/A')}")
    print(f"Bill Date: {bill.get('bill_date', 'N/A')}")
    print(f"Customer: {bill.get('customer_name', 'N/A')}")
    print(f"Total Amount: {bill.get('total_amount', 'N/A')}")
    print()
    
    # Test Delivery Information and Product Association
    deliveries = data.get('deliveries', [])
    print(f"=== FOUND {len(deliveries)} DELIVERIES ===")
    
    total_products_across_deliveries = 0
    
    for i, delivery in enumerate(deliveries):
        print(f"\n--- Delivery {i+1} ---")
        print(f"DDT Series: {delivery.get('ddt_series', 'N/A')}")
        print(f"DDT Number: {delivery.get('ddt_number', 'N/A')}")
        print(f"DDT Date: {delivery.get('ddt_date', 'N/A')}")
        print(f"Model Number: {delivery.get('model_number', 'N/A')}")
        print(f"Product Name: {delivery.get('product_name', 'N/A')}")
        print(f"Product Properties: {delivery.get('product_properties', 'N/A')}")
        
        products = delivery.get('products', [])
        print(f"Associated Products: {len(products)} items")
        total_products_across_deliveries += len(products)
        
        if products:
            print("\nProduct Details:")
            for j, product in enumerate(products[:5]):  # Show first 5 products
                print(f"  {j+1}. Code: {product.get('product_code', 'N/A')}")
                print(f"     Description: {product.get('description', 'N/A')[:100]}{'...' if len(str(product.get('description', ''))) > 100 else ''}")
                print(f"     Unit: {product.get('unit_of_measure', 'N/A')}")
                print(f"     Quantity: {product.get('quantity', 'N/A')}")
                print(f"     Unit Price: {product.get('unit_price', 'N/A')}")
                print(f"     Total Price: {product.get('total_price', 'N/A')}")
                print(f"     Customs Code: {product.get('customs_code', 'N/A')}")
                print()
            
            if len(products) > 5:
                print(f"     ... and {len(products) - 5} more products")
        else:
            print("  No products associated with this delivery")
    
    # Overall Statistics
    print(f"\n=== OVERALL STATISTICS ===")
    print(f"Total Deliveries: {len(deliveries)}")
    print(f"Total Products Across All Deliveries: {total_products_across_deliveries}")
    
    # Check if there are also top-level products (old format)
    top_level_products = data.get('products', [])
    if top_level_products:
        print(f"Top-level Products (legacy): {len(top_level_products)}")
    
    # Parsing Errors
    errors = data.get('parsing_errors', [])
    if errors:
        print(f"\n=== PARSING ERRORS ({len(errors)}) ===")
        for error in errors:
            print(f"  - {error}")
    
    # Raw text sample to see delivery detection
    raw_text = data.get('raw_text', {})
    if raw_text:
        print(f"\n=== RAW TEXT SAMPLE (Page 1) ===")
        page1_text = raw_text.get('page1', '')[:500]
        print(page1_text + "..." if len(page1_text) == 500 else page1_text)
    
    # Save detailed results to file for inspection
    output_file = '/Users/bogdancristianburci/Herd/InvoiceScan/python-parser/test_results_stream.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to: {output_file}")

if __name__ == "__main__":
    test_product_grouping()