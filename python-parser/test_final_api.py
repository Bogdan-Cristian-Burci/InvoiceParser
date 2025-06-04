#!/usr/bin/env python3
"""
Final test of the coordinate-based extraction API.
"""

import requests
import json

def test_api():
    """Test the Flask API endpoint."""
    print("=== TESTING COORDINATE-BASED EXTRACTION API ===")
    
    # Test if Flask is running
    try:
        url = "http://localhost:5000/parse-invoice-coordinate-based"
        invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
        
        with open(invoice_path, 'rb') as f:
            files = {'file': f}
            
            response = requests.post(url, files=files, timeout=30)
            
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success')}")
            
            if result.get('success'):
                data = result.get('data', {})
                products = data.get('products', [])
                debug_info = data.get('debug_info', {})
                
                print(f"\n=== EXTRACTION RESULTS ===")
                print(f"Extraction method: {data.get('extraction_method')}")
                print(f"Products extracted: {len(products)}")
                print(f"Total amount: {debug_info.get('total_amount', 0):.2f}")
                
                print(f"\n=== PRODUCT SUMMARY ===")
                for i, product in enumerate(products):
                    print(f"\nProduct {i+1}:")
                    print(f"  Code: {product.get('product_code')}")
                    print(f"  Description: {product.get('description', '')[:50]}...")
                    print(f"  Total: {product.get('total_price')}")
                
                # Verify we got all 9 products
                if len(products) == 9:
                    print(f"\n✓ SUCCESS: All 9 products extracted via API!")
                else:
                    print(f"\n✗ WARNING: Expected 9 products, got {len(products)}")
                    
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Flask API is not running at http://localhost:5000")
        print("Please start the Flask server with: python app.py")
    except Exception as e:
        print(f"Error testing Flask API: {e}")

if __name__ == "__main__":
    test_api()