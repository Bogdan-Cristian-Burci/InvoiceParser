"""
Coordinate-based table extractor for invoice PDFs.

This module implements a coordinate-based approach to table extraction:
1. Searches for table positioned between "MS5LH0002 3635" and "MS5LH0002 3636" markers
2. Detects table headers with borders to establish column coordinates
3. Extracts row data using established column boundaries
"""

import logging
import pdfplumber
from typing import Dict, List, Optional, Tuple, Any
import re


logger = logging.getLogger(__name__)


class CoordinateTableExtractor:
    """
    Coordinate-based table extractor that uses header detection to map column boundaries.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Expected header mappings - updated to match actual PDF headers
        self.header_mappings = {
            'Prodotto/Var/Tg': 'product_code',
            'Voce dog': 'voce_dog',  # Additional column
            'UM': 'unit_of_measure', 
            'Qtà fatt': 'quantity',
            'Prezzo unitario': 'unit_price',
            'Importo': 'total_price'
        }
        
        # Table boundary markers
        self.start_marker = "MS5LH0002 3635"
        self.end_marker = "MS5LH0002 3636"
        
    def extract_table_data(self, pdf_path: str) -> Dict[str, Any]:
        """
        Main extraction method that processes the PDF and extracts table data.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing extraction results
        """
        try:
            self.logger.info(f"Starting coordinate-based extraction for: {pdf_path}")
            
            with pdfplumber.open(pdf_path) as pdf:
                results = {
                    'success': False,
                    'extraction_method': 'coordinate_based',
                    'table_found': False,
                    'headers_detected': False,
                    'column_coordinates': {},
                    'extracted_rows': [],
                    'parsing_errors': []
                }
                
                # Process each page to find the table
                for page_num, page in enumerate(pdf.pages):
                    self.logger.info(f"Processing page {page_num + 1}")
                    
                    # Look for table boundaries
                    table_bounds = self._find_table_boundaries(page)
                    if not table_bounds:
                        continue
                    
                    results['table_found'] = True
                    self.logger.info(f"Table found on page {page_num + 1}")
                    
                    # Try to use pdfplumber's table extraction first
                    table_area = page.within_bbox((
                        table_bounds['x0'],
                        table_bounds['y0'],
                        table_bounds['x1'],
                        table_bounds['y1']
                    ))
                    
                    # Use pdfplumber's extract_tables with custom settings
                    tables = table_area.extract_tables({
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "snap_tolerance": 3,
                        "join_tolerance": 3,
                        "edge_min_length": 3,
                        "min_words_vertical": 1,
                        "min_words_horizontal": 1,
                    })
                    
                    if tables and len(tables) > 0:
                        # Process the first table found
                        table = tables[0]
                        if table and len(table) > 0:
                            # First row should be headers
                            header_row = table[0]
                            self.logger.info(f"Found header row: {header_row}")
                            
                            # Map column indices to column names
                            column_mapping = self._map_headers_to_columns(header_row)
                            if column_mapping:
                                results['headers_detected'] = True
                                results['column_coordinates'] = column_mapping
                                
                                # Extract data rows (skip header)
                                # Process ALL rows and merge paired rows
                                raw_rows = []
                                for row_idx, row in enumerate(table[1:]):
                                    # Always add the row, even if it seems empty
                                    # The merging logic will handle combining rows
                                    raw_row = {
                                        'row_index': row_idx + 1,
                                        'raw_data': row
                                    }
                                    
                                    # Process columns based on mapping
                                    for column_name, idx in column_mapping.items():
                                        if idx < len(row):
                                            value = row[idx] if row[idx] else ''
                                            if isinstance(value, str):
                                                value = value.strip()
                                            raw_row[column_name] = value
                                        else:
                                            raw_row[column_name] = ''
                                    
                                    raw_rows.append(raw_row)
                                    self.logger.debug(f"Raw row {row_idx + 1}: {raw_row}")
                                
                                self.logger.info(f"Extracted {len(raw_rows)} raw rows before merging")
                                
                                # Merge paired rows (odd rows often contain supplementary data)
                                extracted_rows = self._merge_paired_rows(raw_rows)
                                
                                results['extracted_rows'] = extracted_rows
                                results['row_detection_method'] = 'pdfplumber_tables'
                                
                                if extracted_rows:
                                    results['success'] = True
                                    self.logger.info(f"Extracted {len(extracted_rows)} rows successfully")
                    
                    # Only process first table found
                    break
                
                if not results['table_found']:
                    results['parsing_errors'].append("No table found between specified markers")
                elif not results['headers_detected']:
                    results['parsing_errors'].append("Could not detect table headers")
                elif not results['extracted_rows']:
                    results['parsing_errors'].append("No data rows extracted")
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error in coordinate-based extraction: {e}", exc_info=True)
            return {
                'success': False,
                'extraction_method': 'coordinate_based',
                'error': str(e),
                'parsing_errors': [f"Extraction failed: {str(e)}"]
            }
    
    def _map_headers_to_columns(self, header_row: List[str]) -> Dict[str, int]:
        """
        Map header row to column indices.
        
        Args:
            header_row: List of header values
            
        Returns:
            Dictionary mapping column names to indices
        """
        try:
            column_mapping = {}
            
            for idx, header in enumerate(header_row):
                if header:
                    header_text = header.strip()
                    # Check if this header matches any expected header
                    for expected_header, column_name in self.header_mappings.items():
                        if expected_header in header_text or header_text in expected_header:
                            column_mapping[column_name] = idx
                            self.logger.debug(f"Mapped header '{header_text}' at index {idx} to column '{column_name}'")
                            break
            
            # Handle special cases - description is typically the second column
            if 'product_code' in column_mapping and column_mapping['product_code'] == 0:
                # Check if there's an empty column that could be description
                for idx in range(1, min(4, len(header_row))):
                    if not header_row[idx] or not header_row[idx].strip():
                        column_mapping['description'] = idx
                        self.logger.debug(f"Mapped empty column at index {idx} to 'description'")
                        break
            
            return column_mapping
            
        except Exception as e:
            self.logger.error(f"Error mapping headers: {e}")
            return {}
    
    def _process_table_row(self, row: List[str], column_mapping: Dict[str, int]) -> Dict[str, str]:
        """
        Process a table row using column mapping.
        
        Args:
            row: List of row values
            column_mapping: Dictionary mapping column names to indices
            
        Returns:
            Dictionary with extracted row data
        """
        try:
            row_data = {}
            
            for column_name, idx in column_mapping.items():
                if idx < len(row):
                    value = row[idx] if row[idx] else ''
                    # Clean up the value
                    if isinstance(value, str):
                        value = value.strip()
                    row_data[column_name] = value
                else:
                    row_data[column_name] = ''
            
            return row_data
            
        except Exception as e:
            self.logger.error(f"Error processing row: {e}")
            return {}
    
    def _merge_paired_rows(self, raw_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Merge paired rows where odd rows contain supplementary data for the preceding even row.
        
        The pattern in the PDF is:
        - Row 1: Partial data (often just numeric values)
        - Row 2: Main product data with product code
        - Row 3: Partial data for next product
        - Row 4: Next product's main data
        
        Args:
            raw_rows: List of all extracted rows
            
        Returns:
            List of merged product rows
        """
        merged_rows = []
        i = 0
        
        while i < len(raw_rows):
            current_row = raw_rows[i].copy()
            
            # Check if current row has a product code
            has_product_code = current_row.get('product_code', '').strip() and 'MMA' in current_row.get('product_code', '')
            
            if has_product_code:
                # This is a main product row
                # Check if previous row has supplementary data
                if i > 0:
                    prev_row = raw_rows[i - 1]
                    # Merge numeric values from previous row if current row is missing them
                    if not current_row.get('quantity') and prev_row.get('quantity'):
                        current_row['quantity'] = prev_row['quantity']
                    if not current_row.get('unit_price') and prev_row.get('unit_price'):
                        current_row['unit_price'] = prev_row['unit_price']
                    if not current_row.get('total_price') and prev_row.get('total_price'):
                        current_row['total_price'] = prev_row['total_price']
                    if not current_row.get('unit_of_measure') and prev_row.get('unit_of_measure'):
                        current_row['unit_of_measure'] = prev_row['unit_of_measure']
                    if not current_row.get('voce_dog') and prev_row.get('voce_dog'):
                        current_row['voce_dog'] = prev_row['voce_dog']
                
                merged_rows.append(current_row)
            else:
                # This might be a supplementary row
                # Check if next row has a product code
                if i + 1 < len(raw_rows):
                    next_row = raw_rows[i + 1]
                    if next_row.get('product_code', '').strip() and 'MMA' in next_row.get('product_code', ''):
                        # Next row is a product row, so this is supplementary data
                        # Skip this row as it will be merged when processing the next row
                        pass
                    else:
                        # This might be a product without clear product code in first column
                        # Add it as is
                        merged_rows.append(current_row)
                else:
                    # Last row, add it if it has meaningful data
                    if any(current_row.get(field, '').strip() for field in ['quantity', 'unit_price', 'total_price']):
                        merged_rows.append(current_row)
            
            i += 1
        
        self.logger.info(f"Merged {len(raw_rows)} raw rows into {len(merged_rows)} product rows")
        return merged_rows
    
    def _find_table_boundaries(self, page) -> Optional[Dict[str, float]]:
        """
        Find table boundaries by searching for marker texts.
        Ensures we only get the FIRST table between MS5LH0002 3635 and MS5LH0002 3636.
        
        Args:
            page: pdfplumber page object
            
        Returns:
            Dictionary with table boundaries or None if not found
        """
        try:
            # Extract all text with coordinates
            chars = page.chars
            
            # Find all occurrences of both markers
            start_markers = []
            end_markers = []
            
            # Look for all start and end markers
            for char in chars:
                text = char.get('text', '')
                if text in self.start_marker:
                    # Check if we have the full marker nearby
                    y_pos = char['y0']
                    nearby_text = self._get_text_near_position(page, char['x0'], y_pos, radius=50)
                    if self.start_marker in nearby_text:
                        start_markers.append({
                            'y': y_pos,
                            'x': char['x0'],
                            'text': nearby_text
                        })
                        self.logger.debug(f"Found start marker at y={y_pos}")
                
                if text in self.end_marker:
                    y_pos = char['y0']
                    nearby_text = self._get_text_near_position(page, char['x0'], y_pos, radius=50)
                    if self.end_marker in nearby_text:
                        end_markers.append({
                            'y': y_pos,
                            'x': char['x0'],
                            'text': nearby_text
                        })
                        self.logger.debug(f"Found end marker at y={y_pos}")
            
            # Sort markers by Y coordinate (top to bottom)
            start_markers.sort(key=lambda m: m['y'])
            end_markers.sort(key=lambda m: m['y'])
            
            # Find the first valid pair - start marker followed by end marker
            if start_markers and end_markers:
                first_start = start_markers[0]
                
                # Find the first end marker that comes after the first start marker
                for end_marker in end_markers:
                    if end_marker['y'] > first_start['y']:
                        # Ensure y0 < y1 (y coordinates increase from top to bottom in PDF)
                        y0 = min(first_start['y'], end_marker['y'])
                        y1 = max(first_start['y'], end_marker['y'])
                        # Add a buffer to ensure we capture rows that might be just after the end marker
                        y1 += 50  # Add 50 units buffer to capture any trailing rows
                        self.logger.info(f"Using FIRST table between y={y0} and y={y1} (with buffer)")
                        return {
                            'x0': 0,
                            'y0': y0,
                            'x1': page.width,
                            'y1': y1
                        }
                
                # If no end marker found after start, check if we have reversed coordinates
                # In PDFs, sometimes text appears in reverse order
                for end_marker in end_markers:
                    if end_marker['y'] < first_start['y']:
                        # We have reversed markers - swap them
                        y0 = min(first_start['y'], end_marker['y'])
                        y1 = max(first_start['y'], end_marker['y'])
                        # Add a buffer to ensure we capture rows that might be just after the end marker
                        y1 += 50  # Add 50 units buffer to capture any trailing rows
                        self.logger.info(f"Using FIRST table between y={y0} and y={y1} (reversed markers, with buffer)")
                        return {
                            'x0': 0,
                            'y0': y0,
                            'x1': page.width,
                            'y1': y1
                        }
            
            self.logger.warning("No valid marker pair found for table boundaries")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding table boundaries: {e}")
            return None
    
    def _get_text_near_position(self, page, x: float, y: float, radius: float = 50) -> str:
        """
        Get text near a specific position.
        
        Args:
            page: pdfplumber page object
            x, y: Position coordinates
            radius: Search radius
            
        Returns:
            Concatenated text near the position
        """
        try:
            nearby_chars = []
            for char in page.chars:
                char_x = char.get('x0', 0)
                char_y = char.get('y0', 0)
                
                distance = ((char_x - x) ** 2 + (char_y - y) ** 2) ** 0.5
                if distance <= radius:
                    nearby_chars.append(char)
            
            # Sort by position and concatenate
            nearby_chars.sort(key=lambda c: (c.get('y0', 0), c.get('x0', 0)))
            return ''.join(char.get('text', '') for char in nearby_chars)
            
        except Exception as e:
            self.logger.error(f"Error getting nearby text: {e}")
            return ""
    
    def convert_to_laravel_format(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert coordinate-based extraction results to Laravel-compatible format.
        Returns only the products data from the table extraction.
        
        Args:
            extraction_result: Raw extraction results from coordinate-based extraction
            
        Returns:
            Dictionary in Laravel-expected format with only products data
        """
        try:
            if not extraction_result.get('success', False):
                return {
                    'success': False,
                    'error': 'Extraction failed',
                    'data': extraction_result
                }
            
            extracted_rows = extraction_result.get('extracted_rows', [])
            
            # Convert rows to products format
            products = []
            for row in extracted_rows:
                # Get raw values
                product_code_raw = row.get('product_code', '').strip()
                description = row.get('description', '').strip()
                
                # Parse product code and description
                product_code, extracted_desc = self._parse_product_code_and_description(product_code_raw)
                
                # Use extracted description if no description column value
                if not description and extracted_desc:
                    description = extracted_desc
                
                product = {
                    'product_code': product_code,
                    'description': description,
                    'material': row.get('voce_dog', '').strip() if row.get('voce_dog') else None,
                    'unit_of_measure': row.get('unit_of_measure', '').strip(),
                    'quantity': self._parse_decimal(row.get('quantity', '0')),
                    'unit_price': self._parse_decimal(row.get('unit_price', '0')),
                    'total_price': self._parse_decimal(row.get('total_price', '0')),
                    'width_cm': None  # Not extracted in coordinate method
                }
                
                # Add all rows, even those with partial data
                products.append(product)
            
            laravel_response = {
                'success': True,
                'data': {
                    'extraction_method': 'coordinate_based',
                    'row_detection_method': extraction_result.get('row_detection_method', 'unknown'),
                    'products': products,
                    'parsing_errors': extraction_result.get('parsing_errors', []),
                    'debug_info': {
                        'table_found': extraction_result.get('table_found', False),
                        'headers_detected': extraction_result.get('headers_detected', False),
                        'column_coordinates': extraction_result.get('column_coordinates', {}),
                        'rows_extracted': len(products),
                        'total_amount': sum(p['total_price'] for p in products if p['total_price'])
                    }
                },
                'message': f'Coordinate-based extraction successful. Extracted {len(products)} products from table.'
            }
            
            self.logger.info(f"Converted to Laravel format: {len(products)} products extracted")
            return laravel_response
            
        except Exception as e:
            self.logger.error(f"Error converting to Laravel format: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Format conversion failed: {str(e)}',
                'data': extraction_result
            }
    
    def _parse_product_code_and_description(self, product_code_raw: str) -> Tuple[str, str]:
        """
        Parse product code and description from raw product code field.
        The product code is typically the first part that matches a pattern like MMA00.xxxx.xxxx
        
        Args:
            product_code_raw: Raw product code string that may contain description
            
        Returns:
            Tuple of (product_code, description)
        """
        if not product_code_raw:
            return '', ''
        
        # Pattern for product codes (MMA followed by numbers and dots)
        product_code_pattern = r'(MMA\d+\.\d+\.\d+(?:\s*/\s*\w+\s*/\s*\d+)?)'
        
        # Try to find product code pattern
        match = re.search(product_code_pattern, product_code_raw)
        
        if match:
            product_code = match.group(1).strip()
            # Everything after the product code is description
            description_start = match.end()
            description = product_code_raw[description_start:].strip()
            
            # Clean up description - remove leading dashes or colons
            description = re.sub(r'^[-:\s]+', '', description)
            
            return product_code, description
        else:
            # If no pattern match, check if it starts with a description
            # (like "Filo per impunture...")
            lines = product_code_raw.split('\n')
            if len(lines) > 1:
                # Check if second line contains product code
                for i, line in enumerate(lines[1:], 1):
                    match = re.search(product_code_pattern, line)
                    if match:
                        # First lines are description, this line has product code
                        description = '\n'.join(lines[:i]).strip()
                        product_code = match.group(1).strip()
                        # Add any text after product code to description
                        remainder = line[match.end():].strip()
                        if remainder:
                            description += '\n' + remainder
                        # Add remaining lines to description
                        if i + 1 < len(lines):
                            description += '\n' + '\n'.join(lines[i+1:])
                        return product_code, description
            
            # No clear pattern found, return as is
            return product_code_raw, ''
    
    def _parse_decimal(self, value: str) -> float:
        """
        Parse decimal value from string, handling various formats.
        
        Args:
            value: String value to parse
            
        Returns:
            Parsed decimal value or 0.0 if parsing fails
        """
        try:
            if not value or not isinstance(value, str):
                return 0.0
            
            # Clean the value - handle European number format
            # First, remove thousand separators (dots in European format)
            cleaned = value.strip()
            
            # Handle European format: 1.234,56 -> 1234.56
            if ',' in cleaned and '.' in cleaned:
                # If both comma and dot exist, assume European format
                # Remove dots (thousand separators) and replace comma with dot
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                # Only comma exists, replace with dot
                cleaned = cleaned.replace(',', '.')
            
            # Remove any remaining non-numeric characters except decimal point and minus
            import re
            cleaned = re.sub(r'[^\d.-]', '', cleaned)
            
            if not cleaned:
                return 0.0
            
            return float(cleaned)
            
        except (ValueError, TypeError):
            self.logger.warning(f"Could not parse decimal value: '{value}', returning 0.0")
            return 0.0