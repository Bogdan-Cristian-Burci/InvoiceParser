#!/usr/bin/env python3
"""
Debug script to analyze raw table extraction before merging.
"""

import pdfplumber
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def analyze_raw_extraction():
    """
    Analyze raw table extraction to understand the missing rows.
    """
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    print(f"\n=== ANALYZING RAW TABLE EXTRACTION ===")
    
    with pdfplumber.open(invoice_path) as pdf:
        page = pdf.pages[0]
        
        # Find table boundaries
        text = page.extract_text()
        lines = text.split('\n')
        
        start_y = None
        end_y = None
        
        # Find markers
        for char in page.chars:
            nearby_text = ''.join([c['text'] for c in page.chars if abs(c['y0'] - char['y0']) < 2])
            if "MS5LH0002 3635" in nearby_text and start_y is None:
                start_y = char['y0']
                print(f"Start marker at y={start_y}")
            elif "MS5LH0002 3636" in nearby_text and end_y is None:
                end_y = char['y0']
                print(f"End marker at y={end_y}")
        
        if start_y and end_y:
            # Ensure proper order
            y0 = min(start_y, end_y)
            y1 = max(start_y, end_y)
            
            print(f"\nExtracting table between y={y0} and y={y1}")
            
            # Extract table within boundaries
            table_area = page.within_bbox((0, y0, page.width, y1))
            
            # Try different extraction methods
            print("\n=== METHOD 1: With lines strategy ===")
            tables1 = table_area.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "edge_min_length": 3,
                "min_words_vertical": 1,
                "min_words_horizontal": 1,
            })
            
            if tables1:
                table = tables1[0]
                print(f"Found table with {len(table)} rows (including header)")
                print("\nAll rows:")
                for i, row in enumerate(table):
                    # Check if row has meaningful data
                    has_data = any(cell and cell.strip() for cell in row)
                    if has_data:
                        print(f"Row {i}: {row}")
            
            print("\n=== METHOD 2: With text strategy ===")
            tables2 = table_area.extract_tables({
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
            })
            
            if tables2:
                table = tables2[0]
                print(f"Found table with {len(table)} rows (including header)")
                
            print("\n=== METHOD 3: Default extraction ===")
            tables3 = table_area.extract_tables()
            
            if tables3:
                table = tables3[0]
                print(f"Found table with {len(table)} rows (including header)")
                
                # Count rows with product codes
                product_rows = 0
                for row in table[1:]:  # Skip header
                    if row and len(row) > 0 and row[0]:
                        if 'MMA' in str(row[0]) or any(cell and 'MMA' in str(cell) for cell in row):
                            product_rows += 1
                
                print(f"Rows containing product codes: {product_rows}")

if __name__ == "__main__":
    analyze_raw_extraction()