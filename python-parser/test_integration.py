#!/usr/bin/env python3
"""
Test integration between Python parser and coordinate-based extraction.
"""

import requests
import json
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.extractors.coordinate_table_extractor import CoordinateTableExtractor

def test_direct_extraction():
    """Test coordinate extraction directly."""
    print("=== DIRECT EXTRACTION TEST ===")
    
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    extractor = CoordinateTableExtractor()
    result = extractor.extract_table_data(invoice_path)
    
    print(f"Success: {result.get('success')}")
    print(f"Headers detected: {result.get('headers_detected')}")
    print(f"Rows extracted: {len(result.get('extracted_rows', []))}")
    
    # Convert to Laravel format
    laravel_result = extractor.convert_to_laravel_format(result)
    print(f"\nLaravel format success: {laravel_result.get('success')}")
    print(f"Products extracted: {len(laravel_result.get('data', {}).get('products', []))}")
    
    if laravel_result.get('success'):
        products = laravel_result['data']['products']
        print("\nFirst 3 products:")
        for i, product in enumerate(products[:3]):
            print(f"\nProduct {i+1}:")
            print(f"  Code: {product.get('product_code')}")
            print(f"  Quantity: {product.get('quantity')}")
            print(f"  Unit Price: {product.get('unit_price')}")
            print(f"  Total: {product.get('total_price')}")

def test_flask_api():
    """Test Flask API endpoint."""
    print("\n\n=== FLASK API TEST ===")
    
    # Test if Flask is running
    try:
        url = "http://localhost:5000/parse-invoice-coordinate-based"
        invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
        
        with open(invoice_path, 'rb') as f:
            files = {'file': f}
            
            response = requests.post(url, files=files, timeout=30)
            
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success')}")
            if result.get('success'):
                products = result.get('data', {}).get('products', [])
                print(f"Products extracted: {len(products)}")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Flask API is not running at http://localhost:5000")
    except Exception as e:
        print(f"Error testing Flask API: {e}")

if __name__ == "__main__":
    test_direct_extraction()
    test_flask_api()