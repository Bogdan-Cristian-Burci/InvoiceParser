#!/usr/bin/env python3
"""
Analysis of current extraction results based on user's provided data.
"""

def analyze_current_extraction():
    """Analyze the current results you provided."""
    
    print("CURRENT EXTRACTION RESULTS ANALYSIS")
    print("=" * 60)
    
    # Data from your latest extraction results
    current_products = [
        {
            "product_code": "Interno adesivo - Rinforzo colli",
            "quantity": "52.66", 
            "unit_price": "2.41", 
            "total_price": "126.911"
        },
        {
            "product_code": "Filo per impunture - Titolo 240",
            "quantity": "34.19",
            "unit_price": "0.486", 
            "total_price": "16.616"
        },
        {
            "product_code": "Etichetta a nr. - Etichetta bandi",
            "quantity": "171",
            "unit_price": "0.017",
            "total_price": "2.907"
        }
    ]
    
    # Expected values from the original table
    expected_products = [
        {
            "product_code": "MMA00.1700035.508918",
            "description": "Interno adesivo - Rinforzo colli", 
            "quantity": "52.66",
            "unit_price": "2.41",
            "total_price": "126.911"
        },
        {
            "product_code": "MMA00.1700040.402031",
            "description": "Interno adesivo - Tela elastica s",
            "quantity": "50.6", 
            "unit_price": "1.736",
            "total_price": "87.842"
        },
        {
            "product_code": "MMA00.3000440.402092", 
            "description": "Filo per impunture - Titolo 120",
            "quantity": "21.1978",
            "unit_price": "0.766", 
            "total_price": "16.238"
        },
        {
            "product_code": "MMA00.3000650.402101",
            "description": "Filo per impunture - Titolo 240",
            "quantity": "34.19",
            "unit_price": "0.486",
            "total_price": "16.616"
        },
        {
            "product_code": "MMA00.3100279.517167",
            "description": "Etichetta a nr. - Etichetta bandi", 
            "quantity": "171",
            "unit_price": "0.017",
            "total_price": "2.907"
        }
    ]
    
    print("\nCURRENT RESULTS:")
    print("Product | Quantity  | Unit Price | Total Price | Status")
    print("--------|-----------|------------|-------------|--------")
    
    for i, product in enumerate(current_products):
        qty = product['quantity']
        unit = product['unit_price'] 
        total = product['total_price']
        
        # Validate math
        try:
            calc_total = float(qty) * float(unit)
            actual_total = float(total)
            math_ok = abs(calc_total - actual_total) < 0.01
            math_status = "✅" if math_ok else "❌"
        except:
            math_status = "?"
            
        print(f"{i+1:7d} | {qty:>9} | {unit:>10} | {total:>11} | {math_status}")
    
    print("\nEXPECTED RESULTS:")
    print("Product | Quantity  | Unit Price | Total Price | Product Code")
    print("--------|-----------|------------|-------------|-------------")
    
    for i, product in enumerate(expected_products):
        qty = product['quantity']
        unit = product['unit_price']
        total = product['total_price']
        code = product['product_code']
        
        print(f"{i+1:7d} | {qty:>9} | {unit:>10} | {total:>11} | {code}")
    
    print("\nCOMPARISON ANALYSIS:")
    print("=" * 60)
    
    # Find matches in the current vs expected
    print("\n✅ CORRECT NUMERIC VALUES FOUND:")
    for i, current in enumerate(current_products):
        for j, expected in enumerate(expected_products):
            if (current['quantity'] == expected['quantity'] and 
                current['unit_price'] == expected['unit_price'] and
                current['total_price'] == expected['total_price']):
                
                print(f"  Current Product {i+1} matches Expected Row {j+1}")
                print(f"    Values: {current['quantity']} × {current['unit_price']} = {current['total_price']}")
                print(f"    Product: {expected['product_code']} ({expected['description']})")
                print()
    
    print("❌ ISSUES IDENTIFIED:")
    print("  1. Product codes and descriptions are swapped")
    print("     - Current 'product_code' field contains descriptions")
    print("     - Actual product codes (MMA00.xxx) are in 'description' field")
    print()
    print("  2. Missing products from table")
    print("     - Expected 5 products, only getting 3")
    print("     - Missing: Row 2 (MMA00.1700040) and Row 3 (MMA00.3000440)")
    print()
    print("  3. Row sequence issues") 
    print("     - Getting Row 1, Row 4, Row 5")
    print("     - Skipping Row 2 and Row 3")

    print("\n🔍 NUMERIC ACCURACY:")
    print("  ✅ Row 1: 52.66 × 2.41 = 126.911 (PERFECT)")
    print("  ✅ Row 4: 34.19 × 0.486 = 16.616 (PERFECT)")  
    print("  ✅ Row 5: 171 × 0.017 = 2.907 (PERFECT)")
    print("  📊 The numeric values that ARE extracted are mathematically correct!")

if __name__ == "__main__":
    analyze_current_extraction()