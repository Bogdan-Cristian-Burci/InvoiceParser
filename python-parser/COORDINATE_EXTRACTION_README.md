# Coordinate-Based Table Extraction

## Overview
The coordinate-based extraction method is designed to extract product data from tables located between specific markers in PDF invoices.

## Implementation Details

### Table Detection
- Searches for tables between markers "MS5LH0002 3635" and "MS5LH0002 3636"
- Handles cases where Y-coordinates might be reversed in the PDF
- Extracts only the FIRST table found between these markers

### Header Mapping
The extractor recognizes the following headers:
- `Prodotto/Var/Tg` → `product_code`
- `Voce dog` → `voce_dog` (used for material field)
- `UM` → `unit_of_measure`
- `Qtà fatt` → `quantity`
- `Prezzo unitario` → `unit_price`
- `Importo` → `total_price`

### Data Processing
- Uses pdfplumber's built-in table extraction with custom settings
- Automatically detects and maps column indices based on headers
- Handles empty columns (e.g., description column)
- Parses decimal values with comma separators (European format)

### Output Format
Returns only product data without bill/delivery information:
```json
{
  "success": true,
  "data": {
    "extraction_method": "coordinate_based",
    "products": [
      {
        "product_code": "MMA00.1700040.402031",
        "description": "Interno adesivo - Tela elastica s",
        "material": "5903.9091",
        "unit_of_measure": "MT",
        "quantity": 50.6,
        "unit_price": 1.736,
        "total_price": 87.842,
        "width_cm": null
      }
    ],
    "debug_info": {
      "table_found": true,
      "headers_detected": true,
      "rows_extracted": 7,
      "total_amount": 202.977
    }
  }
}
```

## Usage

### Direct Python Usage
```python
from src.extractors.coordinate_table_extractor import CoordinateTableExtractor

extractor = CoordinateTableExtractor()
result = extractor.extract_table_data("path/to/invoice.pdf")
laravel_format = extractor.convert_to_laravel_format(result)
```

### Flask API Endpoint
```bash
curl -X POST http://localhost:5000/parse-invoice-coordinate-based \
  -F "file=@path/to/invoice.pdf"
```

## Key Features
- Robust table detection between specific markers
- Automatic header detection and column mapping
- Handles European decimal format (comma as decimal separator)
- Returns clean product data ready for Laravel integration
- Includes debug information for troubleshooting