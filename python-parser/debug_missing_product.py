#!/usr/bin/env python3
"""
Debug script to find the missing 9th product.
"""

import pdfplumber

def debug_missing_product():
    """Debug why we're missing the 9th product."""
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    print("\n=== DEBUGGING MISSING PRODUCT ===")
    
    with pdfplumber.open(invoice_path) as pdf:
        page = pdf.pages[0]
        
        # Find markers and get boundaries with buffer
        start_y = None
        end_y = None
        
        for char in page.chars:
            nearby_text = ''.join([c['text'] for c in page.chars if abs(c['y0'] - char['y0']) < 2])
            if "MS5LH0002 3635" in nearby_text and start_y is None:
                start_y = char['y0']
            elif "MS5LH0002 3636" in nearby_text and end_y is None:
                end_y = char['y0']
        
        # Apply boundaries with buffer
        y0 = min(start_y, end_y)
        y1 = max(start_y, end_y) + 20  # Buffer
        
        print(f"Boundaries: y0={y0}, y1={y1}")
        
        # Extract table
        table_area = page.within_bbox((0, y0, page.width, y1))
        tables = table_area.extract_tables({
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3,
            "min_words_vertical": 1,
            "min_words_horizontal": 1,
        })
        
        if tables:
            table = tables[0]
            print(f"\nExtracted table has {len(table)} rows")
            
            # Look specifically at the last few rows
            print("\nLast 5 rows:")
            for i, row in enumerate(table[-5:], len(table)-5):
                print(f"Row {i}: {row}")
            
            # Count MMA products
            mma_count = 0
            for row in table:
                if any('MMA' in str(cell) for cell in row if cell):
                    mma_count += 1
                    if 'MMA25.2052222' in str(row):
                        print(f"\nFound missing product in row: {row}")
            
            print(f"\nTotal MMA products in extracted table: {mma_count}")
        
        # Also check the full page table
        print("\n\n=== CHECKING FULL PAGE TABLE ===")
        full_tables = page.extract_tables()
        if len(full_tables) >= 2:
            full_table = full_tables[1]
            print(f"Full page table 2 has {len(full_table)} rows")
            
            # Check if the missing product is in the full table
            for i, row in enumerate(full_table):
                if any('MMA25.2052222' in str(cell) for cell in row if cell):
                    print(f"\nMissing product found in full table at row {i}: {row}")

if __name__ == "__main__":
    debug_missing_product()