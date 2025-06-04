#!/usr/bin/env python3
"""
Analyze the merging pattern to understand how to extract all 19 products.
"""

import pdfplumber
import sys
import os
import re

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def analyze_merging_pattern():
    """
    Analyze the pattern of rows to understand proper merging.
    """
    invoice_path = "/Users/bogdancristianburci/Herd/InvoiceScan/laravel-app/storage/app/public/invoices/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf"
    
    print(f"\n=== ANALYZING MERGING PATTERN ===")
    
    with pdfplumber.open(invoice_path) as pdf:
        page = pdf.pages[0]
        
        # Find table boundaries
        start_y = None
        end_y = None
        
        # Find markers
        for char in page.chars:
            nearby_text = ''.join([c['text'] for c in page.chars if abs(c['y0'] - char['y0']) < 2])
            if "MS5LH0002 3635" in nearby_text and start_y is None:
                start_y = char['y0']
            elif "MS5LH0002 3636" in nearby_text and end_y is None:
                end_y = char['y0']
        
        if start_y and end_y:
            # Ensure proper order
            y0 = min(start_y, end_y)
            y1 = max(start_y, end_y)
            
            # Extract table within boundaries
            table_area = page.within_bbox((0, y0, page.width, y1))
            
            # Extract table
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
                print(f"Found table with {len(table)} rows")
                
                # Analyze pattern
                products = []
                pending_data = {}
                
                for i, row in enumerate(table[1:]):  # Skip header
                    row_num = i + 1
                    
                    # Extract data from row
                    col0 = row[0] if len(row) > 0 else None
                    col3 = row[3] if len(row) > 3 else None  # Voce dog
                    col4 = row[4] if len(row) > 4 else None  # UM
                    col5 = row[5] if len(row) > 5 else None  # Quantity
                    col6 = row[6] if len(row) > 6 else None  # Unit price
                    col7 = row[7] if len(row) > 7 else None  # Total
                    
                    # Check if this row has a product code
                    has_product_code = col0 and 'MMA' in str(col0)
                    
                    print(f"\nRow {row_num}:")
                    print(f"  Col0 (Product): {col0}")
                    print(f"  Has product code: {has_product_code}")
                    
                    if has_product_code:
                        # This is a main product row
                        product = {
                            'row_num': row_num,
                            'product_code_raw': col0,
                            'voce_dog': col3,
                            'um': col4,
                            'quantity': col5,
                            'unit_price': col6,
                            'total': col7
                        }
                        
                        # If we have pending data from previous row, merge it
                        if pending_data and not product['quantity'] and pending_data.get('quantity'):
                            product['quantity'] = pending_data['quantity']
                            product['unit_price'] = pending_data.get('unit_price')
                            product['total'] = pending_data.get('total')
                            product['merged_from'] = pending_data['row_num']
                        
                        products.append(product)
                        pending_data = {}
                    else:
                        # This might be supplementary data
                        if col4 or col5 or col6 or col7:  # Has some data
                            pending_data = {
                                'row_num': row_num,
                                'voce_dog': col3,
                                'um': col4,
                                'quantity': col5,
                                'unit_price': col6,
                                'total': col7
                            }
                
                print(f"\n=== EXTRACTED PRODUCTS ===")
                print(f"Total products found: {len(products)}")
                
                for i, product in enumerate(products):
                    print(f"\nProduct {i+1}:")
                    print(f"  Row: {product['row_num']}")
                    if 'merged_from' in product:
                        print(f"  Merged from row: {product['merged_from']}")
                    print(f"  Product code raw: {product['product_code_raw'][:50]}...")
                    print(f"  Quantity: {product['quantity']}")
                    print(f"  Unit price: {product['unit_price']}")
                    print(f"  Total: {product['total']}")

if __name__ == "__main__":
    analyze_merging_pattern()