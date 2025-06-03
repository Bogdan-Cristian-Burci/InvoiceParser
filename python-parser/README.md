# Invoice PDF Parser Service v2.0

A modular, step-based PDF invoice parsing service built with Flask that extracts structured data from invoice PDFs.

## Architecture

The service follows a clean, modular architecture with separate steps for different processing phases:

### Step-by-Step Processing Pipeline

1. **General Metadata Extraction** - Extract bill/invoice header information
2. **Page-by-Page Processing** - Extract table data from each PDF page
3. **OCR Validation** - Validate extracted data using OCR cross-referencing
4. **Response Compilation** - Compile final structured response

### Project Structure

```
python-parser/
├── app.py                      # Main Flask application
├── requirements.txt           # Python dependencies
├── Dockerfile                # Container configuration
├── src/
│   ├── invoice_processor.py   # Main orchestrator
│   ├── models/
│   │   └── invoice_models.py  # Data models and configurations
│   ├── extractors/
│   │   ├── metadata_extractor.py    # Step 1: General metadata
│   │   ├── table_extractor.py       # Step 2: Page-by-page tables
│   │   └── response_compiler.py     # Step 4: Final compilation
│   ├── validators/
│   │   └── ocr_validator.py         # Step 3: OCR validation
│   └── utils/
│       ├── helpers.py               # Utility functions
│       ├── pdf_utils.py             # PDF processing utilities
│       └── config.py                # Configuration management
```

## Features

### Core Functionality
- **Modular Design**: Clean separation of concerns with individual modules
- **Error Isolation**: Problems in one step don't break the entire pipeline
- **Step-by-Step Processing**: Each phase can be debugged and optimized independently
- **Configuration Management**: Environment-based configuration for all settings
- **OCR Validation**: Cross-reference extracted data with raw text for accuracy
- **Partial Results**: Can return partial data even if some steps fail

### Data Extraction
- Bill/invoice metadata (number, date, currency, customer info)
- Delivery note information (DDT numbers, model codes)
- Product line items (codes, descriptions, quantities, prices)
- Footer information (totals, weights, shipping terms)
- Checksum validation for data integrity

### API Endpoints
- `GET /health` - Service health check
- `GET /config` - Current configuration (for debugging)
- `POST /parse-invoice` - Main invoice parsing endpoint
- `POST /parse-invoice/stats` - Parse with detailed processing statistics

## Configuration

Configure the service using environment variables:

### OCR Validation
- `ENABLE_OCR_VALIDATION` (default: true) - Enable OCR cross-validation
- `OCR_CONFIDENCE_THRESHOLD` (default: 0.8) - Minimum confidence for validation

### Table Extraction  
- `TABLE_EXTRACTION_FLAVOR` (default: "lattice") - Camelot extraction method
- `LINE_SCALE` (default: 30) - Line detection sensitivity

### Processing Limits
- `MAX_PAGES_TO_PROCESS` (default: null) - Limit number of pages processed
- `VALIDATE_CHECKSUMS` (default: true) - Enable total amount validation

## Usage

### Docker Deployment
```bash
docker-compose up python-parser
```

### Local Development
```bash
cd python-parser
pip install -r requirements.txt
python app.py
```

### API Example
```bash
curl -X POST -F "file=@invoice.pdf" http://localhost:5000/parse-invoice
```

## Response Format

The service returns Laravel-compatible JSON responses:

```json
{
  "success": true,
  "data": {
    "bill": {
      "bill_number": "502",
      "bill_date": "19-05-2025",
      "currency": "EUR",
      "customer_code": "MSCE00068",
      "customer_name": "S.C. TEXBRA SRL",
      "total_amount": "15473.37"
    },
    "delivery": {
      "ddt_number": "MS5LH0002 3635",
      "ddt_date": "19-05-2025",
      "model_code": "CAMICIA ELIOT"
    },
    "products": [
      {
        "product_code": "MMA00.1700035.508918",
        "description": "Interno adesivo - Rinforzo colli",
        "quantity": "52.66",
        "unit_price": "2.41",
        "total_price": "126.911"
      }
    ],
    "validation_checksum_ok": true,
    "parsing_errors": []
  },
  "message": "Invoice parsing completed successfully."
}
```

## Benefits of New Architecture

### For Development
- **Maintainability**: Each module has a single responsibility
- **Testability**: Individual components can be unit tested
- **Debuggability**: Easy to isolate and fix issues in specific steps
- **Extensibility**: New extraction methods or validation steps can be added easily

### For Production
- **Reliability**: Partial results even if some steps fail
- **Monitoring**: Detailed statistics and error reporting per step
- **Performance**: Can optimize individual steps independently
- **Configuration**: Runtime configuration without code changes

### For Users
- **Better Error Messages**: Specific error reporting per processing step
- **Data Quality**: OCR validation ensures higher accuracy
- **Partial Recovery**: Get usable data even from problematic PDFs
- **Transparency**: Clear indication of which steps succeeded/failed

## Migration from v1.0

The new modular architecture maintains API compatibility while providing:
- Better error handling and reporting
- Improved data accuracy through OCR validation
- Configurable processing pipeline
- Enhanced debugging capabilities
- More robust partial failure handling

The original monolithic parser has been preserved as `app_old.py` for reference.