#!/usr/bin/env python3
"""
Verify the coordinate extraction is working correctly.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.extractors.coordinate_table_extractor import CoordinateTableExtractor
import json

def verify_extraction():
    """Verify extraction works correctly."""
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    print("=== VERIFYING COORDINATE EXTRACTION ===")
    
    # Initialize extractor
    extractor = CoordinateTableExtractor()
    
    # Extract data
    result = extractor.extract_table_data(invoice_path)
    
    # Convert to Laravel format
    laravel_result = extractor.convert_to_laravel_format(result)
    
    # Print results
    print(f"\nExtraction success: {laravel_result.get('success')}")
    
    if laravel_result.get('success'):
        data = laravel_result['data']
        products = data['products']
        
        print(f"Products extracted: {len(products)}")
        print(f"\nJSON Response Preview:")
        print(json.dumps({
            'success': laravel_result['success'],
            'data': {
                'extraction_method': data['extraction_method'],
                'products': [
                    {
                        'product_code': p['product_code'],
                        'total_price': p['total_price']
                    } for p in products[:3]
                ] + ['... and {} more products'.format(len(products) - 3)],
                'debug_info': data['debug_info']
            }
        }, indent=2))
        
        # Verify count
        if len(products) == 9:
            print(f"\n✓ SUCCESS: All 9 products extracted correctly!")
        else:
            print(f"\n✗ WARNING: Expected 9 products, got {len(products)}")

if __name__ == "__main__":
    verify_extraction()