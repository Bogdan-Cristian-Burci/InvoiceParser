#!/usr/bin/env python3
"""
Debug script to scan for all tables and products in the PDF.
"""

import pdfplumber
import re

def scan_all_tables():
    """
    Scan all tables in the PDF to find all products.
    """
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    print(f"\n=== SCANNING ALL TABLES IN PDF ===")
    
    with pdfplumber.open(invoice_path) as pdf:
        all_products = []
        
        for page_num, page in enumerate(pdf.pages):
            print(f"\n--- Page {page_num + 1} ---")
            
            # Extract all tables on this page
            tables = page.extract_tables()
            
            print(f"Found {len(tables)} tables on page {page_num + 1}")
            
            for table_num, table in enumerate(tables):
                product_count = 0
                
                for row in table:
                    # Check if any cell contains MMA product code
                    row_text = ' '.join([str(cell) if cell else '' for cell in row])
                    if re.search(r'MMA\d+\.\d+\.\d+', row_text):
                        product_count += 1
                        all_products.append({
                            'page': page_num + 1,
                            'table': table_num + 1,
                            'row': row,
                            'text': row_text[:100]
                        })
                
                if product_count > 0:
                    print(f"  Table {table_num + 1}: {len(table)} rows, {product_count} products")
        
        print(f"\n=== TOTAL PRODUCTS FOUND: {len(all_products)} ===")
        
        # Group by page and table
        for i, product in enumerate(all_products):
            print(f"\nProduct {i+1} - Page {product['page']}, Table {product['table']}:")
            print(f"  {product['text']}...")
            
        # Also check for MS5LH0002 markers
        print("\n=== CHECKING FOR BOUNDARY MARKERS ===")
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if "MS5LH0002 3635" in text:
                print(f"Start marker found on page {page_num + 1}")
            if "MS5LH0002 3636" in text:
                print(f"End marker found on page {page_num + 1}")

if __name__ == "__main__":
    scan_all_tables()