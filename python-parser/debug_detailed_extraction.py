#!/usr/bin/env python3
"""
Debug script for detailed extraction analysis.
"""

import sys
import os
import logging

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.extractors.coordinate_table_extractor import CoordinateTableExtractor

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def debug_extraction():
    """
    Debug the coordinate-based extraction with detailed output.
    """
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    print(f"Debugging extraction for: {invoice_path}")
    
    # Initialize extractor
    extractor = CoordinateTableExtractor()
    
    # Run extraction
    result = extractor.extract_table_data(invoice_path)
    
    print("\n=== EXTRACTION RESULT ===")
    print(f"Success: {result.get('success', False)}")
    print(f"Table found: {result.get('table_found', False)}")
    print(f"Headers detected: {result.get('headers_detected', False)}")
    print(f"Raw rows extracted: {len(result.get('extracted_rows', []))}")
    
    if result.get('extracted_rows'):
        print("\n=== EXTRACTED ROWS (after merging) ===")
        for i, row in enumerate(result['extracted_rows']):
            print(f"\nRow {i+1}:")
            print(f"  Product Code: {row.get('product_code', '')}")
            print(f"  Description: {row.get('description', '')}")
            print(f"  Voce Dog: {row.get('voce_dog', '')}")
            print(f"  UM: {row.get('unit_of_measure', '')}")
            print(f"  Quantity: {row.get('quantity', '')}")
            print(f"  Unit Price: {row.get('unit_price', '')}")
            print(f"  Total Price: {row.get('total_price', '')}")
    
    # Convert to Laravel format
    laravel_result = extractor.convert_to_laravel_format(result)
    
    print("\n=== LARAVEL FORMAT ===")
    print(f"Success: {laravel_result.get('success', False)}")
    if laravel_result.get('success'):
        products = laravel_result['data']['products']
        print(f"Products: {len(products)}")
        
        print("\n=== FINAL PRODUCTS ===")
        for i, product in enumerate(products):
            print(f"\nProduct {i+1}:")
            print(f"  Code: {product.get('product_code')}")
            print(f"  Description: {product.get('description')}")
            print(f"  Material: {product.get('material')}")
            print(f"  UM: {product.get('unit_of_measure')}")
            print(f"  Quantity: {product.get('quantity')}")
            print(f"  Unit Price: {product.get('unit_price')}")
            print(f"  Total: {product.get('total_price')}")

if __name__ == "__main__":
    debug_extraction()