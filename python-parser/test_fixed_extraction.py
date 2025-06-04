#!/usr/bin/env python3
"""
Test the fixed coordinate extraction to ensure we get all 9 products.
"""

import sys
import os
import logging

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.extractors.coordinate_table_extractor import CoordinateTableExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_extraction():
    """Test coordinate extraction with the fixed logic."""
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    print("\n=== TESTING FIXED EXTRACTION ===")
    
    extractor = CoordinateTableExtractor()
    result = extractor.extract_table_data(invoice_path)
    
    print(f"\nExtraction success: {result.get('success')}")
    print(f"Raw rows extracted: {len(result.get('extracted_rows', []))}")
    
    # Convert to Laravel format
    laravel_result = extractor.convert_to_laravel_format(result)
    
    if laravel_result.get('success'):
        products = laravel_result['data']['products']
        print(f"\nTotal products extracted: {len(products)}")
        
        print("\n=== ALL PRODUCTS ===")
        for i, product in enumerate(products):
            print(f"\nProduct {i+1}:")
            print(f"  Code: {product.get('product_code')}")
            print(f"  Description: {product.get('description')}")
            print(f"  Quantity: {product.get('quantity')}")
            print(f"  Unit Price: {product.get('unit_price')}")
            print(f"  Total: {product.get('total_price')}")
        
        # Check if we got all expected products
        expected_codes = [
            "MMA00.1700040.402031",
            "MMA00.3000650.402101",
            "MMA00.3100381.552853",
            "MMA00.4200001.416572",
            "MMA00.5100004.517066",  # XXX / 002
            "MMA00.5100004.517066",  # XXX / 004
            "MMA00.5100102.460937",
            "MMA25.1052194.560120",
            "MMA25.2052222.560767"
        ]
        
        extracted_codes = [p['product_code'].split(' / ')[0] for p in products]
        
        print(f"\n=== VALIDATION ===")
        print(f"Expected products: {len(expected_codes)}")
        print(f"Extracted products: {len(extracted_codes)}")
        
        missing = []
        for code in expected_codes:
            if code not in extracted_codes:
                missing.append(code)
        
        if missing:
            print(f"\nMissing products: {missing}")
        else:
            print("\n✓ All expected products extracted successfully!")

if __name__ == "__main__":
    test_extraction()