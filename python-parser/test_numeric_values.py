#!/usr/bin/env python3
"""
Test script to isolate and analyze numeric values (quantity, unit_price, total_price)
from the table extraction to verify row alignment is working correctly.
"""

import json
import sys
import os

def analyze_numeric_values():
    """Analyze the numeric values from the current extraction results."""
    
    # Read the current results
    try:
        with open('../sample_invoice_data.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: sample_invoice_data.json not found")
        return
    
    print("NUMERIC VALUES ANALYSIS")
    print("=" * 60)
    
    deliveries = data.get('response_data', {}).get('data', {}).get('deliveries', [])
    
    for i, delivery in enumerate(deliveries):
        products = delivery.get('products', [])
        if not products:
            continue
            
        print(f"\nDelivery {i+1}: {delivery.get('ddt_series')} {delivery.get('ddt_number')}")
        print(f"Products: {len(products)}")
        print("-" * 40)
        
        for j, product in enumerate(products[:10]):  # Show first 10 products
            qty = product.get('quantity', 'N/A')
            unit_price = product.get('unit_price', 'N/A')
            total_price = product.get('total_price', 'N/A')
            
            print(f"Product {j+1:2d}: Qty={qty:>8} | Unit={unit_price:>8} | Total={total_price:>10}")
            
            # Validate the math if all values are present
            if qty != 'N/A' and unit_price != 'N/A' and total_price != 'N/A':
                try:
                    calc_total = float(qty) * float(unit_price)
                    actual_total = float(total_price)
                    diff = abs(calc_total - actual_total)
                    
                    if diff > 0.01:  # Allow for small rounding differences
                        print(f"            ❌ MATH ERROR: {float(qty)} × {float(unit_price)} = {calc_total:.3f} ≠ {actual_total}")
                    else:
                        print(f"            ✅ Math correct: {float(qty)} × {float(unit_price)} = {calc_total:.3f}")
                except ValueError:
                    print(f"            ⚠️  Could not validate math (non-numeric values)")
        
        if len(products) > 10:
            print(f"... and {len(products) - 10} more products")

def analyze_expected_values():
    """Show what the expected values should be based on the original table data."""
    
    print("\n\nEXPECTED VALUES (from original table)")
    print("=" * 60)
    
    # Expected values from the manual table inspection you provided earlier
    expected = [
        {"row": 1, "qty": "52.66", "unit": "2.41", "total": "126.911", "product": "MMA00.1700035.508918 (Interno adesivo - Rinforzo colli)"},
        {"row": 2, "qty": "50.6", "unit": "1.736", "total": "87.842", "product": "MMA00.1700040.402031 (Interno adesivo - Tela elastica)"},
        {"row": 3, "qty": "21.1978", "unit": "0.766", "total": "16.238", "product": "MMA00.3000440.402092 (Filo per impunture - Titolo 120)"},
        {"row": 4, "qty": "34.19", "unit": "0.486", "total": "16.616", "product": "MMA00.3000650.402101 (Filo per impunture - Titolo 240)"},
        {"row": 5, "qty": "171", "unit": "0.017", "total": "2.907", "product": "MMA00.3100279.517167 (Etichetta a nr. - Etichetta bandi)"},
    ]
    
    print("Row | Quantity  | Unit Price | Total     | Product")
    print("----|-----------|------------|-----------|----------")
    for exp in expected:
        print(f"{exp['row']:3d} | {exp['qty']:>9} | {exp['unit']:>10} | {exp['total']:>9} | {exp['product']}")

def compare_with_actual():
    """Compare expected vs actual values to check alignment."""
    
    print("\n\nCOMPARISON: Expected vs Actual")
    print("=" * 60)
    
    try:
        with open('../sample_invoice_data.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: sample_invoice_data.json not found")
        return
    
    # Get first delivery products
    first_delivery = data.get('response_data', {}).get('data', {}).get('deliveries', [{}])[0]
    products = first_delivery.get('products', [])
    
    # Expected values for first 5 products
    expected_values = [
        ("52.66", "2.41", "126.911"),
        ("50.6", "1.736", "87.842"), 
        ("21.1978", "0.766", "16.238"),
        ("34.19", "0.486", "16.616"),
        ("171", "0.017", "2.907")
    ]
    
    print("Product | Expected (Qty|Unit|Total)      | Actual (Qty|Unit|Total)       | Status")
    print("--------|-------------------------------|------------------------------|--------")
    
    for i in range(min(5, len(products))):
        exp_qty, exp_unit, exp_total = expected_values[i] if i < len(expected_values) else ("?", "?", "?")
        
        actual_qty = products[i].get('quantity', 'N/A')
        actual_unit = products[i].get('unit_price', 'N/A')
        actual_total = products[i].get('total_price', 'N/A')
        
        # Check if values match
        qty_match = str(actual_qty) == exp_qty
        unit_match = str(actual_unit) == exp_unit  
        total_match = str(actual_total) == exp_total
        
        status = "✅ PERFECT" if all([qty_match, unit_match, total_match]) else "❌ MISMATCH"
        
        print(f"{i+1:7d} | {exp_qty:>8}|{exp_unit:>8}|{exp_total:>9} | {actual_qty:>8}|{actual_unit:>8}|{actual_total:>9} | {status}")

if __name__ == "__main__":
    analyze_numeric_values()
    analyze_expected_values()
    compare_with_actual()