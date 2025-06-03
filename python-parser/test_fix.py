#!/usr/bin/env python3
import sys
import os
import json
import logging

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.invoice_processor import InvoiceProcessor
from src.utils.config import ConfigManager

# Set up minimal logging
logging.basicConfig(level=logging.WARNING)
# Set table extractor to info to see key messages
logging.getLogger('src.extractors.table_extractor').setLevel(logging.INFO)

def test_fixed_extraction():
    """Test the fixed table extraction logic."""
    
    # Path to test invoice
    pdf_path = "../laravel-app/public/invoice/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return
    
    # Initialize processor
    config = ConfigManager.load_config()
    processor = InvoiceProcessor(config)
    
    print(f"Processing: {pdf_path}")
    print("=" * 50)
    
    try:
        # Process the invoice
        result_dict = processor.process_invoice(pdf_path)
        
        # Focus on the first delivery's products to check if the fix worked
        if result_dict.get('data', {}).get('deliveries'):
            first_delivery = result_dict['data']['deliveries'][0]
            print(f"First delivery: {first_delivery.get('ddt_series')} {first_delivery.get('ddt_number')}")
            print(f"Number of products: {len(first_delivery.get('products', []))}")
            print()
            
            # Check first few products
            for i, product in enumerate(first_delivery.get('products', [])[:3]):
                print(f"Product {i+1}:")
                print(f"  Code: {product.get('product_code')}")
                print(f"  Quantity: {product.get('quantity')}")
                print(f"  Unit Price: {product.get('unit_price')}")
                print(f"  Total Price: {product.get('total_price')}")
                print(f"  Unit of Measure: {product.get('unit_of_measure')}")
                print()
        
        # Save result to file for inspection
        with open('test_results_fixed.json', 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)
        
        print("Results saved to test_results_fixed.json")
        
    except Exception as e:
        print(f"Error processing invoice: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_extraction()