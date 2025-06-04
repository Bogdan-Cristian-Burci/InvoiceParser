#!/usr/bin/env python3
"""
Debug script to understand table row extraction.
"""

import pdfplumber
import logging
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def analyze_table_extraction():
    """
    Analyze table extraction to understand why we're missing rows.
    """
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    print(f"\n=== ANALYZING TABLE EXTRACTION ===")
    print(f"File: {invoice_path}")
    
    with pdfplumber.open(invoice_path) as pdf:
        # Process first page
        page = pdf.pages[0]
        
        # Find table between markers
        text = page.extract_text()
        lines = text.split('\n')
        
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            if "MS5LH0002 3635" in line:
                start_idx = i
                print(f"Start marker found at line {i}: {line[:80]}")
            if "MS5LH0002 3636" in line and start_idx is not None:
                end_idx = i
                print(f"End marker found at line {i}: {line[:80]}")
                break
        
        if start_idx and end_idx:
            print(f"\nTable content between lines {start_idx} and {end_idx}:")
            print("=" * 80)
            for i in range(start_idx + 1, min(start_idx + 25, end_idx)):
                print(f"Line {i-start_idx}: {lines[i]}")
            print("=" * 80)
        
        # Extract tables using pdfplumber
        tables = page.extract_tables()
        
        print(f"\n\nFound {len(tables)} tables on page")
        
        # Analyze the table that should contain our products
        if len(tables) >= 2:
            table = tables[1]  # Second table typically contains products
            print(f"\nAnalyzing table with {len(table)} rows")
            print("\nFirst 20 rows of the table:")
            print("=" * 100)
            
            for i, row in enumerate(table[:20]):
                print(f"Row {i}: {row}")
                # Check if this row has product data
                has_data = False
                for j, cell in enumerate(row):
                    if cell and cell.strip():
                        if j == 0 and 'MMA' in cell:  # Product code column
                            has_data = True
                        elif j == 4:  # UM column
                            has_data = True
                        elif j == 5 or j == 6 or j == 7:  # Quantity, price columns
                            has_data = True
                
                if has_data:
                    print(f"  --> This row contains product data")
            
            print("=" * 100)
            
            # Try with different extraction settings
            print("\n\nTrying different extraction settings...")
            
            # Text-based extraction
            text_tables = page.extract_tables({
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
            })
            
            if text_tables and len(text_tables) > 1:
                text_table = text_tables[1]
                print(f"\nText-based extraction: {len(text_table)} rows")
                print("First 10 rows:")
                for i, row in enumerate(text_table[:10]):
                    print(f"Row {i}: {row}")

if __name__ == "__main__":
    analyze_table_extraction()