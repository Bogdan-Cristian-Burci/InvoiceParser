#!/usr/bin/env python3
"""
Debug script to analyze PDF structure and table boundaries.
"""

import pdfplumber
import logging
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def analyze_pdf_structure(pdf_path):
    """
    Analyze PDF structure to understand table layout.
    """
    print(f"\n=== PDF STRUCTURE ANALYSIS ===")
    print(f"File: {pdf_path}")
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            print(f"\n=== PAGE {page_num + 1} ===")
            print(f"Dimensions: {page.width} x {page.height}")
            
            # Search for table markers
            text = page.extract_text()
            if text:
                # Find MS5LH0002 3635 and MS5LH0002 3636 positions
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if "MS5LH0002 3635" in line:
                        print(f"Found start marker at line {i}: {line[:100]}")
                    if "MS5LH0002 3636" in line:
                        print(f"Found end marker at line {i}: {line[:100]}")
            
            # Look for tables
            tables = page.extract_tables()
            if tables:
                print(f"\nFound {len(tables)} tables using extract_tables()")
                for i, table in enumerate(tables):
                    print(f"\nTable {i+1}: {len(table)} rows")
                    if table and len(table) > 0:
                        # Print first few rows
                        for j, row in enumerate(table[:5]):
                            print(f"  Row {j}: {row}")
                        if len(table) > 5:
                            print(f"  ... {len(table) - 5} more rows")
            
            # Look for lines/borders
            lines = page.lines
            horizontal_lines = [line for line in lines if abs(line['y0'] - line['y1']) < 2]
            vertical_lines = [line for line in lines if abs(line['x0'] - line['x1']) < 2]
            
            print(f"\nLines found:")
            print(f"  Horizontal: {len(horizontal_lines)}")
            print(f"  Vertical: {len(vertical_lines)}")
            
            # Try to find table area between markers
            print("\n=== SEARCHING FOR TABLE BETWEEN MARKERS ===")
            
            # Get all text with positions
            chars = page.chars
            
            # Find marker positions
            start_y = None
            end_y = None
            
            text_objects = []
            current_text = ""
            current_x = None
            current_y = None
            
            for char in sorted(chars, key=lambda c: (c['y0'], c['x0'])):
                if current_y is None or abs(char['y0'] - current_y) > 5:
                    # New line
                    if current_text:
                        text_objects.append({
                            'text': current_text,
                            'x': current_x,
                            'y': current_y
                        })
                    current_text = char['text']
                    current_x = char['x0']
                    current_y = char['y0']
                else:
                    current_text += char['text']
            
            # Add last text object
            if current_text:
                text_objects.append({
                    'text': current_text,
                    'x': current_x,
                    'y': current_y
                })
            
            # Find markers
            for obj in text_objects:
                if "MS5LH0002 3635" in obj['text']:
                    start_y = obj['y']
                    print(f"Start marker found at y={start_y}")
                if "MS5LH0002 3636" in obj['text']:
                    end_y = obj['y']
                    print(f"End marker found at y={end_y}")
            
            if start_y and end_y:
                # Ensure start_y is less than end_y
                if start_y > end_y:
                    start_y, end_y = end_y, start_y
                
                print(f"\nTable should be between y={start_y} and y={end_y}")
                
                # Look for text in this region
                table_texts = [obj for obj in text_objects if start_y <= obj['y'] <= end_y]
                
                print(f"\nText objects in table region: {len(table_texts)}")
                
                # Look for potential headers
                print("\n=== POTENTIAL HEADERS ===")
                for obj in table_texts[:10]:  # First 10 lines
                    if any(header in obj['text'] for header in ['Prodotto', 'UM', 'Qtà', 'Prezzo', 'Importo']):
                        print(f"Potential header at y={obj['y']}: {obj['text'][:100]}")
                
                # Try to extract table with custom settings
                print("\n=== TRYING CUSTOM TABLE EXTRACTION ===")
                
                # Crop to table area
                table_area = page.within_bbox((0, start_y, page.width, end_y))
                
                # Try different table extraction settings
                settings = {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "explicit_vertical_lines": [],
                    "explicit_horizontal_lines": [],
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                    "edge_min_length": 3,
                    "min_words_vertical": 1,
                    "min_words_horizontal": 1,
                }
                
                custom_tables = table_area.extract_tables(settings)
                if custom_tables:
                    print(f"Found {len(custom_tables)} tables with custom settings")
                    for i, table in enumerate(custom_tables):
                        print(f"\nCustom Table {i+1}: {len(table)} rows")
                        for j, row in enumerate(table[:5]):
                            print(f"  Row {j}: {row}")
                
                # Try text-based extraction
                print("\n=== TEXT-BASED TABLE EXTRACTION ===")
                settings2 = {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                }
                
                text_tables = table_area.extract_tables(settings2)
                if text_tables:
                    print(f"Found {len(text_tables)} tables with text strategy")
                    for i, table in enumerate(text_tables):
                        print(f"\nText Table {i+1}: {len(table)} rows")
                        for j, row in enumerate(table[:5]):
                            print(f"  Row {j}: {row}")

if __name__ == "__main__":
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    analyze_pdf_structure(invoice_path)