# Claude Development Context

## Project Overview
InvoiceScan is a Laravel + Python microservice for processing PDF invoices. It extracts structured data including bill information, delivery notes, and product details from Italian business invoices.

### Architecture
- **Laravel App**: Frontend API and file handling (`laravel-app/`)
- **Python Parser**: PDF processing microservice (`python-parser/`)
- **Docker**: Containerized deployment with nginx proxy

## Recent Work (June 3, 2025)

### Critical Issue Fixed: Table Extraction Row Misalignment

**Problem**: 
- Product 2 was getting quantity/price data from table Row 5 instead of Row 2
- Example: Product 1 had correct data (qty: 52.66, price: 2.41, total: 126.911)
- Product 2 had wrong data from Row 5 (qty: 171, price: 0.017, total: 2.907)

**Root Cause Analysis**:
1. Poor row boundary detection - couldn't identify where products start/end
2. Cross-row contamination - numeric values from different rows mixed together
3. Missing column structure validation - ignored proper header mapping
4. Flexible extraction too permissive - identified wrong text as product codes

**Solution Implemented**:
- **File**: `python-parser/src/extractors/table_extractor.py:578-707`
- **Changes**: Complete rewrite of `_extract_products_from_table()` method
- **New Approach**: 
  1. Try structured extraction first (uses proper column mapping)
  2. Enhanced flexible extraction as fallback (better row alignment)
  3. Stricter product code validation: `^[A-Z]{2,3}[A-Z0-9.]+$`
  4. Same-row-only numeric extraction (no cross-row contamination)
  5. Require minimum 3 numeric values per product

**Status**: ✅ Code implemented and improved further

**Latest Update (June 3, 2025 - Follow-up)**:
- ✅ **Numeric alignment fixed** - Products now get correct row data
- ✅ **Mathematical accuracy confirmed** - All extracted values are correct
- ❌ **Field swapping issue identified** - product_code ↔ description fields reversed
- ❌ **Missing rows issue** - Only extracting 3/5 expected products

**Additional Fix Implemented**:
- Enhanced MMA product code detection to find codes anywhere in cell content
- Added proper product description pattern matching
- Improved handling of swapped product_code/description fields
- Better row detection to capture missing products

## Key Project Files

### Python Parser Core
- `src/invoice_processor.py` - Main processing pipeline
- `src/extractors/table_extractor.py` - **RECENTLY MODIFIED** - Table/product extraction
- `src/extractors/metadata_extractor.py` - Bill metadata extraction
- `src/extractors/response_compiler.py` - Final response compilation
- `src/models/invoice_models.py` - Data structures

### Configuration & Utils
- `src/utils/config.py` - Environment configuration
- `src/utils/helpers.py` - Utility functions (Italian decimal parsing, etc.)
- `src/utils/pdf_utils.py` - PDF text extraction
- `app.py` - Flask API endpoints

### Laravel Integration
- `laravel-app/app/Services/InvoicePdfScannerService.php` - Python service integration
- `laravel-app/app/Http/Controllers/BillController.php` - API endpoints

## Testing

### Quick Test (Current Fix)
```bash
cd python-parser
python3 test_fix.py  # Tests the table extraction fixes
```

### Full API Test
```bash
# From laravel-app directory
curl -X POST http://localhost:8000/api/bills/scan-pdf \
  -F "file=@public/invoice/sample.pdf"
```

### Sample Invoice Location
- Test file: `laravel-app/public/invoice/L. V._2025.05.19 - nr. 502 15473.37 €_46 colli_(297.50 Kg_N, 328 Kg_B).pdf`

## Known Issues & Dependencies

### Critical Dependencies
- **Ghostscript**: Required for Camelot table extraction
  - Install: Follow https://camelot-py.readthedocs.io/en/master/user/install-deps.html
  - Without it: Table extraction fails, only delivery info extracted

### Environment Setup
```bash
# Python dependencies
cd python-parser
pip install -r requirements.txt

# Laravel dependencies  
cd laravel-app
composer install
npm install
```

## Recent Test Results

### Before Fix (sample_invoice_data.json)
```json
{
  "product_code": "MT",
  "quantity": "52.66",      // Correct
  "unit_price": "2.41",     // Correct  
  "total_price": "126.911"  // Correct
},
{
  "product_code": "NR", 
  "quantity": "171",        // WRONG - from Row 5
  "unit_price": "0.017",    // WRONG - from Row 5
  "total_price": "2.907"    // WRONG - from Row 5
}
```

### Expected After Fix
- Product 2 should get data from Row 2, not Row 5
- Proper row alignment maintained throughout table
- No cross-row contamination of numeric values

## Development Notes

### Logging Configuration
```python
# For debugging table extraction
logging.getLogger('src.extractors.table_extractor').setLevel(logging.DEBUG)
```

### Table Structure Understanding
Invoice tables have this pattern:
```
Row 1: Product Code + Description | Customs Code | Unit | Quantity | Unit Price | Total
Row 2: Product Code + Description | Customs Code | Unit | Quantity | Unit Price | Total
...
```

### Alternative Extraction Methods
1. **Structured**: Uses column headers (preferred when available)
2. **Flexible**: Pattern matching fallback (improved with row alignment)
3. **Text-based**: Raw text parsing (last resort)

## Future Improvements Needed

### High Priority
- [ ] Row grouping logic for multi-row product entries
- [ ] Better handling of product descriptions spanning multiple rows
- [ ] Validation against known invoice formats

### Medium Priority  
- [ ] OCR fallback when table extraction fails completely
- [ ] Improved error handling and recovery
- [ ] Performance optimization for large invoices

## Commit Strategy

When ready to commit the table extraction fix:
```bash
git add python-parser/src/extractors/table_extractor.py
git commit -m "Fix table extraction row misalignment

- Product 2 was getting data from Row 5 instead of Row 2  
- Implemented structured + improved flexible extraction
- Added stricter product code validation
- Eliminated cross-row numeric value contamination
- Requires testing with Ghostscript dependency"
```

---
*This file helps Claude understand the project context and recent changes across sessions.*