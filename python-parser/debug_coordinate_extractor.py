#!/usr/bin/env python3
"""
Debug script for coordinate-based table extractor.
"""

import logging
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.extractors.coordinate_table_extractor import CoordinateTableExtractor

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def debug_coordinate_extraction():
    """
    Debug the coordinate-based extraction on the sample invoice.
    """
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    if not os.path.exists(invoice_path):
        print(f"Invoice file not found: {invoice_path}")
        return
    
    print(f"Debugging coordinate extraction for: {invoice_path}")
    
    # Initialize extractor
    extractor = CoordinateTableExtractor()
    
    # Run extraction with debug output
    result = extractor.extract_table_data(invoice_path)
    
    print("\n=== EXTRACTION RESULT ===")
    print(f"Success: {result.get('success', False)}")
    print(f"Table found: {result.get('table_found', False)}")
    print(f"Headers detected: {result.get('headers_detected', False)}")
    print(f"Column coordinates: {result.get('column_coordinates', {})}")
    print(f"Extracted rows: {len(result.get('extracted_rows', []))}")
    print(f"Parsing errors: {result.get('parsing_errors', [])}")
    
    if result.get('extracted_rows'):
        print("\n=== EXTRACTED ROWS ===")
        for i, row in enumerate(result['extracted_rows']):
            print(f"Row {i+1}: {row}")

if __name__ == "__main__":
    debug_coordinate_extraction()