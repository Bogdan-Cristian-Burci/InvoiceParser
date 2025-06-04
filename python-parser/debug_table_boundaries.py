#!/usr/bin/env python3
"""
Debug table boundaries to understand why we're missing rows.
"""

import pdfplumber
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def debug_boundaries():
    """Debug the table boundaries issue."""
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    print("\n=== DEBUGGING TABLE BOUNDARIES ===")
    
    with pdfplumber.open(invoice_path) as pdf:
        page = pdf.pages[0]
        
        # Find markers
        start_y = None
        end_y = None
        
        for char in page.chars:
            nearby_text = ''.join([c['text'] for c in page.chars if abs(c['y0'] - char['y0']) < 2])
            if "MS5LH0002 3635" in nearby_text and start_y is None:
                start_y = char['y0']
            elif "MS5LH0002 3636" in nearby_text and end_y is None:
                end_y = char['y0']
        
        print(f"Start marker Y: {start_y}")
        print(f"End marker Y: {end_y}")
        
        # Ensure proper order
        y0 = min(start_y, end_y) if start_y and end_y else None
        y1 = max(start_y, end_y) if start_y and end_y else None
        
        print(f"\nTable boundaries: y0={y0}, y1={y1}")
        
        if y0 and y1:
            # Extract table within boundaries
            table_area = page.within_bbox((0, y0, page.width, y1))
            
            # Extract ALL tables in this area
            all_tables = table_area.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "edge_min_length": 3,
                "min_words_vertical": 1,
                "min_words_horizontal": 1,
            })
            
            print(f"\nFound {len(all_tables)} tables in bounded area")
            
            for i, table in enumerate(all_tables):
                print(f"\nTable {i+1}: {len(table)} rows")
                
                # Count product rows
                product_count = 0
                for row in table:
                    if any('MMA' in str(cell) for cell in row if cell):
                        product_count += 1
                
                print(f"  Products: {product_count}")
                
                # Show last few rows
                if len(table) > 15:
                    print("\n  Last 5 rows:")
                    for j, row in enumerate(table[-5:], len(table)-5):
                        print(f"    Row {j}: {row}")
            
            # Now extract tables from the full page
            print("\n\n=== FULL PAGE TABLES ===")
            full_tables = page.extract_tables()
            
            print(f"Found {len(full_tables)} tables on full page")
            
            # Look at table 2 which should have all products
            if len(full_tables) >= 2:
                table = full_tables[1]
                print(f"\nTable 2 on full page: {len(table)} rows")
                print("Last 5 rows:")
                for j, row in enumerate(table[-5:], len(table)-5):
                    print(f"  Row {j}: {row}")

if __name__ == "__main__":
    debug_boundaries()