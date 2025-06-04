#!/usr/bin/env python3
"""
Debug script to understand the complete table structure.
"""

import pdfplumber
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def analyze_table_structure():
    """
    Analyze the complete table structure between markers.
    """
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    print(f"\n=== ANALYZING TABLE STRUCTURE ===")
    
    with pdfplumber.open(invoice_path) as pdf:
        # Look at first page
        page = pdf.pages[0]
        
        # Extract all tables
        all_tables = page.extract_tables()
        
        print(f"Found {len(all_tables)} tables on page 1")
        
        # Check which tables are between our markers
        text = page.extract_text()
        
        # Find marker positions in the text
        start_pos = text.find("MS5LH0002 3635")
        end_pos = text.find("MS5LH0002 3636")
        
        print(f"\nStart marker position: {start_pos}")
        print(f"End marker position: {end_pos}")
        
        # Look at each table
        for i, table in enumerate(all_tables):
            print(f"\n=== TABLE {i+1} ===")
            print(f"Rows: {len(table)}")
            
            # Count products in this table
            product_count = 0
            for row in table:
                row_text = ' '.join([str(cell) if cell else '' for cell in row])
                if 'MMA' in row_text:
                    product_count += 1
            
            print(f"Products: {product_count}")
            
            # Show first and last few rows
            if len(table) > 0:
                print("\nFirst 3 rows:")
                for j, row in enumerate(table[:3]):
                    print(f"  Row {j}: {row}")
                
                if len(table) > 6:
                    print("\nLast 3 rows:")
                    for j, row in enumerate(table[-3:], len(table)-3):
                        print(f"  Row {j}: {row}")
        
        # Specifically analyze table 2 which should have our products
        if len(all_tables) >= 2:
            print(f"\n\n=== DETAILED ANALYSIS OF TABLE 2 ===")
            table = all_tables[1]  # Table 2 (0-indexed)
            
            print(f"Total rows: {len(table)}")
            
            # Show all rows with MMA codes
            print("\nAll rows containing MMA codes:")
            for i, row in enumerate(table):
                row_text = ' '.join([str(cell) if cell else '' for cell in row])
                if 'MMA' in row_text:
                    print(f"\nRow {i}:")
                    print(f"  Full row: {row}")
                    # Extract just the product info
                    if len(row) > 0 and row[0]:
                        print(f"  Product column: {row[0][:60]}...")

if __name__ == "__main__":
    analyze_table_structure()