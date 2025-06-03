import re
import os
import logging
import camelot
from typing import List, Optional, Dict, Any
from ..models.invoice_models import PageData, ProductData, DeliveryData, ProcessingConfig
from ..utils.pdf_utils import extract_text_from_page
from ..utils.helpers import parse_italian_decimal, clean_string_field

logger = logging.getLogger(__name__)


class TableExtractor:
    """Extracts table data from individual PDF pages."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
    
    def extract_page_data(self, pdf_path: str, page_number: int) -> PageData:
        """
        Extract all data from a single page.
        page_number is 0-indexed.
        """
        page_data = PageData(page_number=page_number, raw_text="")
        
        try:
            # Extract raw text from page
            page_data.raw_text = extract_text_from_page(pdf_path, page_number)
            
            # NEW APPROACH: Extract ALL delivery info on this page
            # Instead of looking for just one delivery, scan for all delivery patterns
            all_deliveries = self._extract_all_deliveries_from_page(page_data.raw_text)
            
            # For backward compatibility, set delivery_info to the first one found
            page_data.delivery_info = all_deliveries[0] if all_deliveries else None
            
            # Store all found deliveries for later processing
            page_data.all_deliveries = all_deliveries
            
            # Extract tables using Camelot
            page_data.tables = self._extract_tables_camelot(pdf_path, page_number + 1)  # Camelot uses 1-indexed
            
            # Process tables to extract products and associate them with deliveries
            page_data.products = self._process_tables_to_products(page_data.tables, page_number)
            
            # NEW: Associate products with their respective deliveries
            self._associate_products_with_deliveries(page_data)
            
        except Exception as e:
            error_msg = f"Error processing page {page_number + 1}: {str(e)}"
            page_data.errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
        
        return page_data
    
    def _extract_delivery_info(self, page_text: str) -> Optional[DeliveryData]:
        """Extract delivery note information from page text using new field mapping."""
        
        if not page_text:
            logger.debug("No page text provided for delivery extraction")
            return None
        
        # Debug: log the page text to see what we're working with
        logger.debug(f"Page text for delivery extraction (first 500 chars): {page_text[:500]}")
        
        # Look for delivery data section start - try multiple patterns
        delivery_markers = [
            "LISTA VALORIZZATA del DDT interno",
            "LISTA VALORIZZATA (Fattura proforma)", 
            "LISTA VALORIZZATA"
        ]
        
        marker_found = False
        found_marker = None
        for marker in delivery_markers:
            if marker in page_text:
                logger.debug(f"Found delivery section marker: '{marker}'")
                marker_found = True
                found_marker = marker
                break
        
        if not marker_found:
            logger.debug("No delivery section marker found in page text")
            return None
        
        logger.debug(f"Found delivery section marker '{found_marker}', proceeding with extraction")
        
        delivery_data = DeliveryData()
        
        # Extract ddt_series and ddt_number from line like "MS5LH0002 3635"
        # Try multiple patterns to catch different formats
        ddt_patterns = [
            r"([A-Z0-9]{9})\s+(\d+)",           # MS5LH0002 3635
            r"([A-Z0-9]{9})\s*(\d{4})",         # MS5LH0002 3635 (4 digit numbers)
            r"([A-Z0-9]{8,10})\s+(\d+)"        # Flexible length series
        ]
        
        ddt_found = False
        for pattern in ddt_patterns:
            ddt_match = re.search(pattern, page_text)
            if ddt_match:
                delivery_data.ddt_series = ddt_match.group(1).strip()
                delivery_data.ddt_number = ddt_match.group(2).strip()
                logger.debug(f"Found DDT series: {delivery_data.ddt_series}, number: {delivery_data.ddt_number} using pattern: {pattern}")
                ddt_found = True
                break
        
        if not ddt_found:
            logger.debug("DDT series and number pattern not found")
            # Let's log all potential DDT-like patterns we can find for debugging
            all_ddt_matches = re.findall(r"([A-Z0-9]{5,12})\s+(\d+)", page_text)
            if all_ddt_matches:
                logger.debug(f"Found potential DDT patterns that didn't match: {all_ddt_matches[:5]}")  # Show first 5
        
        # Extract ddt_date from line like "Del: 19-05-2025"
        date_match = re.search(r"Del:\s*(\d{2}-\d{2}-\d{4})", page_text)
        if date_match:
            delivery_data.ddt_date = date_match.group(1).strip()
            logger.debug(f"Found DDT date: {delivery_data.ddt_date}")
        else:
            logger.debug("DDT date pattern not found")
        
        # Extract ddt_reason from line after "Causale" (e.g., "CLV")
        reason_match = re.search(r"Causale\s*\n\s*([A-Z]{3})", page_text)
        if reason_match:
            delivery_data.ddt_reason = reason_match.group(1).strip()
            logger.debug(f"Found DDT reason: {delivery_data.ddt_reason}")
        else:
            logger.debug("DDT reason pattern not found")
        
        # Extract model_number, order_series, and order_number from line like "MMM25.221160116.50 / MS5CE0002 1394"
        # Try multiple patterns for model/order data
        model_order_patterns = [
            r"([A-Z0-9.]+)\s*/\s*([A-Z0-9]{9})\s+(\d+)",  # With / separator
            r"([A-Z0-9.]+)\s+([A-Z0-9]{9})\s+(\d+)",      # Without / separator
            r"([A-Z0-9.]+)\s*/\s*([A-Z0-9]+)\s+(\d+)"     # With / and flexible order series length
        ]
        
        model_order_found = False
        for pattern in model_order_patterns:
            model_order_match = re.search(pattern, page_text)
            if model_order_match:
                delivery_data.model_number = model_order_match.group(1).strip()
                delivery_data.order_series = model_order_match.group(2).strip()
                delivery_data.order_number = model_order_match.group(3).strip()
                logger.debug(f"Found model number: {delivery_data.model_number}, order series: {delivery_data.order_series}, order number: {delivery_data.order_number}")
                model_order_found = True
                break
        
        if not model_order_found:
            logger.debug("Model/order pattern not found")
        
        # Extract product_properties from line like "Tessuto: 100% Cotone"
        properties_match = re.search(r"Tessuto:\s*([^\n]+)", page_text)
        if properties_match:
            delivery_data.product_properties = properties_match.group(1).strip()
            logger.debug(f"Found product properties: {delivery_data.product_properties}")
        else:
            logger.debug("Product properties pattern not found")
        
        # Extract product_name - look for the line after properties and before model_name
        # Pattern: properties line, then product_name line, then model_name line
        product_name_match = re.search(r"Tessuto:[^\n]+\n\s*([A-Z]+)\n\s*([A-Z]+)", page_text)
        if product_name_match:
            delivery_data.product_name = product_name_match.group(1).strip()
            delivery_data.model_name = product_name_match.group(2).strip()
            logger.debug(f"Found product name: {delivery_data.product_name}, model name: {delivery_data.model_name}")
        else:
            logger.debug("Product name/model name pattern not found")
        
        # Log the final delivery data state
        logger.debug(f"Final delivery data - DDT series: {delivery_data.ddt_series}, DDT number: {delivery_data.ddt_number}")
        
        # Only return delivery data if we found the essential fields
        if delivery_data.ddt_series and delivery_data.ddt_number:
            logger.debug("Returning valid delivery data")
            return delivery_data
        
        logger.debug("No valid delivery data found - missing essential fields")
        return None
    
    def _extract_all_deliveries_from_page(self, page_text: str) -> List[DeliveryData]:
        """Extract ALL delivery sections found on this page."""
        
        if not page_text:
            return []
        
        deliveries = []
        
        # Strategy: Look for DDT patterns that appear after "DDT interno" to avoid order numbers
        # Use context-aware patterns to only match actual DDT information
        ddt_context_patterns = [
            r"DDT interno\s+([A-Z0-9]{9})\s+(\d{4})",           # After "DDT interno MS5LH0002 3635"
            r"DDT interno\s+([A-Z0-9]{8,10})\s+(\d{3,5})",      # Flexible length after "DDT interno"
            r"del DDT interno\s+([A-Z0-9]{9})\s+(\d{4})",       # After "del DDT interno MS5LH0002 3635"
            r"del DDT interno\s+([A-Z0-9]{8,10})\s+(\d{3,5})"   # Flexible length after "del DDT interno"
        ]
        
        found_ddts = []
        for pattern in ddt_context_patterns:
            matches = re.finditer(pattern, page_text)
            for match in matches:
                ddt_series = match.group(1).strip()
                ddt_number = match.group(2).strip()
                position = match.start()
                found_ddts.append((ddt_series, ddt_number, position))
        
        logger.debug(f"Found {len(found_ddts)} DDT patterns after 'DDT interno': {found_ddts}")
        
        # For each DDT pattern found, try to extract delivery data from surrounding text
        for ddt_series, ddt_number, position in found_ddts:
            # Extract text around this DDT - but be more careful about context
            # Only look for product details AFTER the DDT pattern to avoid cross-contamination
            start_pos = max(0, position - 200)  # Look just 200 chars before for date/reason
            end_pos = min(len(page_text), position + 1500)  # Look 1500 chars after for product details
            surrounding_text = page_text[start_pos:end_pos]
            
            delivery = self._extract_delivery_from_context(surrounding_text, ddt_series, ddt_number, position - start_pos)
            if delivery:
                deliveries.append(delivery)
                logger.debug(f"Successfully extracted delivery: {ddt_series} {ddt_number}")
            else:
                logger.debug(f"Failed to extract complete delivery data for: {ddt_series} {ddt_number}")
        
        # Remove duplicates based on DDT series and number
        unique_deliveries = []
        seen_ddts = set()
        for delivery in deliveries:
            ddt_key = f"{delivery.ddt_series}_{delivery.ddt_number}"
            if ddt_key not in seen_ddts:
                seen_ddts.add(ddt_key)
                unique_deliveries.append(delivery)
        
        logger.info(f"Extracted {len(unique_deliveries)} unique deliveries from page")
        return unique_deliveries
    
    def _extract_delivery_from_context(self, context_text: str, ddt_series: str, ddt_number: str, ddt_position: int = 0) -> Optional[DeliveryData]:
        """Extract delivery data from text context around a known DDT pattern."""
        
        delivery_data = DeliveryData()
        delivery_data.ddt_series = ddt_series
        delivery_data.ddt_number = ddt_number
        
        # Extract ddt_date from line like "Del: 19-05-2025"
        date_match = re.search(r"Del:\s*(\d{2}-\d{2}-\d{4})", context_text)
        if date_match:
            delivery_data.ddt_date = date_match.group(1).strip()
        
        # Extract ddt_reason from line after "Causale" (e.g., "CLV")
        reason_match = re.search(r"Causale\s*\n\s*([A-Z]{3})", context_text)
        if reason_match:
            delivery_data.ddt_reason = reason_match.group(1).strip()
        
        # Extract model_number, order_series, and order_number from line like "MMM25.221160116.50 / MS5CE0002 1394"
        # IMPROVED: Only look for product details AFTER the DDT position to avoid cross-contamination
        text_after_ddt = context_text[ddt_position:] if ddt_position > 0 else context_text
        
        model_order_patterns = [
            r"([A-Z0-9.]+)\s*/\s*([A-Z0-9]{9})\s+(\d+)",  # With / separator
            r"([A-Z0-9.]+)\s+([A-Z0-9]{9})\s+(\d+)",      # Without / separator
            r"([A-Z0-9.]+)\s*/\s*([A-Z0-9]+)\s+(\d+)"     # With / and flexible order series length
        ]
        
        for pattern in model_order_patterns:
            model_order_match = re.search(pattern, text_after_ddt)
            if model_order_match:
                delivery_data.model_number = model_order_match.group(1).strip()
                delivery_data.order_series = model_order_match.group(2).strip()
                delivery_data.order_number = model_order_match.group(3).strip()
                logger.debug(f"Found model/order for {ddt_number}: {delivery_data.model_number}, {delivery_data.order_series}, {delivery_data.order_number}")
                break
        
        # Extract product_properties from line like "Tessuto: 100% Cotone" - also only after DDT
        properties_match = re.search(r"Tessuto:\s*([^\n]+)", text_after_ddt)
        if properties_match:
            delivery_data.product_properties = properties_match.group(1).strip()
        
        # Extract product_name and model_name - also only after DDT
        product_name_match = re.search(r"Tessuto:[^\n]+\n\s*([A-Z]+)\n\s*([A-Z]+)", text_after_ddt)
        if product_name_match:
            delivery_data.product_name = product_name_match.group(1).strip()
            delivery_data.model_name = product_name_match.group(2).strip()
        
        # Log what we found for this delivery
        logger.debug(f"Delivery {ddt_number} extracted - model: {delivery_data.model_number or 'None'}, product: {delivery_data.product_name or 'None'}")
        
        # Return delivery data even if some fields are missing
        # The essential requirement is just DDT series and number (which we already have)
        return delivery_data
    
    def _extract_tables_camelot(self, pdf_path: str, page_number_1_indexed: int) -> List[Any]:
        """Extract tables using Camelot. page_number is 1-indexed."""
        
        try:
            # Build parameters based on flavor
            camelot_params = {
                'pages': str(page_number_1_indexed),
                'flavor': self.config.table_extraction_flavor,
                'suppress_stdout': True
            }
            
            # Only add line_scale for lattice flavor
            if self.config.table_extraction_flavor == 'lattice':
                camelot_params['line_scale'] = self.config.line_scale
            
            tables = camelot.read_pdf(pdf_path, **camelot_params)
            
            logger.info(f"Camelot: Page {page_number_1_indexed} - Found {tables.n} tables in '{os.path.basename(pdf_path)}'")
            
            # DEBUG: Log table details
            for i, table in enumerate(tables):
                df = table.df
                logger.debug(f"Table {i+1}: {df.shape[0]} rows x {df.shape[1]} cols")
                if not df.empty:
                    logger.debug(f"Table {i+1} headers: {df.iloc[0].tolist()}")
                    if len(df) > 1:
                        logger.debug(f"Table {i+1} sample row: {df.iloc[1].tolist()}")
            
            return [table.df for table in tables]
            
        except Exception as e:
            logger.error(f"Error extracting tables with Camelot from page {page_number_1_indexed}: {e}", exc_info=True)
            return []
    
    def _process_tables_to_products(self, tables: List[Any], page_number: int, raw_text: str = "") -> List[ProductData]:
        """Process extracted tables and convert to ProductData objects."""
        
        products = []
        
        logger.debug(f"Processing {len(tables)} tables on page {page_number + 1}")
        
        for table_index, df in enumerate(tables):
            logger.debug(f"Table {table_index + 1}: {df.shape[0]} rows x {df.shape[1]} cols")
            
            if df.empty:
                logger.debug(f"Skipping empty table {table_index + 1} on page {page_number + 1}")
                continue
            
            # For debugging: log table content
            if len(df) > 0:
                logger.debug(f"Table {table_index + 1} first row: {df.iloc[0].tolist()}")
            if len(df) > 1:
                logger.debug(f"Table {table_index + 1} second row: {df.iloc[1].tolist()}")
            
            # Map column headers to our expected fields
            col_map = self._map_table_columns(df)
            logger.debug(f"Table {table_index + 1} column mapping: {col_map}")
            
            # Try to extract products even if not all required columns are present
            # This is more flexible for different table structures
            extracted_products = self._extract_products_from_table(df, table_index, page_number, col_map)
            products.extend(extracted_products)
        
        # Note: Text-based extraction disabled - using table extraction only
        # This provides better results for the specific invoice format
        
        logger.info(f"Extracted {len(products)} total products from page {page_number + 1}")
        return products
    
    def _map_table_columns(self, df) -> Dict[str, str]:
        """Map table column headers to our expected field names."""
        
        header_row_text = df.iloc[0].astype(str).str.lower().str.strip()
        col_map = {}
        
        for i, header_text in enumerate(header_row_text):
            col_name_df = df.columns[i]  # Camelot uses 0, 1, 2... or parsed names
            
            if "prodotto" in header_text:
                col_map['product_code_raw'] = col_name_df
            elif "voce dog" in header_text:
                col_map['customs_code'] = col_name_df
            elif header_text == "um":
                col_map['unit_measure'] = col_name_df
            elif "qtà fatt" in header_text:
                col_map['quantity'] = col_name_df
            elif "prezzo unitario" in header_text:
                col_map['unit_price'] = col_name_df
            elif "importo" in header_text:
                col_map['line_total'] = col_name_df
        
        # Fallback to positional mapping if key headers are missing
        if not all(k in col_map for k in ['product_code_raw', 'quantity', 'unit_price', 'line_total']):
            logger.warning(f"Attempting positional fallback for table columns. Headers: {df.iloc[0].tolist()}")
            
            cols = df.columns
            col_map.setdefault('product_code_raw', cols[0])
            col_map.setdefault('customs_code', cols[2] if len(cols) > 2 else None)
            col_map.setdefault('unit_measure', cols[3] if len(cols) > 3 else None)
            col_map.setdefault('quantity', cols[4] if len(cols) > 4 else None)
            col_map.setdefault('unit_price', cols[5] if len(cols) > 5 else None)
            col_map.setdefault('line_total', cols[6] if len(cols) > 6 else None)
        
        return col_map
    
    def _validate_required_columns(self, col_map: Dict[str, str], table_index: int, page_number: int) -> bool:
        """Validate that required columns are mapped."""
        
        required_cols = ['product_code_raw', 'quantity', 'unit_price', 'line_total']
        missing_cols = [col for col in required_cols if col not in col_map or col_map[col] is None]
        
        if missing_cols:
            logger.warning(f"Skipping table {table_index + 1} on page {page_number + 1} due to missing columns: {missing_cols}")
            return False
        
        return True
    
    def _extract_product_from_row(self, df, row_index: int, col_map: Dict[str, str]) -> Optional[ProductData]:
        """Extract a ProductData object from a table row."""
        
        try:
            row_data = df.iloc[row_index]
            
            # Extract and clean product code
            product_code_raw_val = str(row_data[col_map['product_code_raw']]).strip()
            product_lines = product_code_raw_val.split('\n')
            actual_product_code = product_lines[0].strip()
            
            # Skip if no actual product code or looks like footer
            if not actual_product_code or actual_product_code.lower().startswith("total"):
                return None
            
            # Extract line total and skip if empty
            line_total_val_str = str(row_data.get(col_map['line_total'], "")).strip()
            if not line_total_val_str or line_total_val_str.lower() == 'nan':
                return None
            
            # Build description from multiple sources
            description = self._build_product_description(df, row_data, row_index, col_map, product_lines)
            
            # Create ProductData object
            product = ProductData()
            product.product_code = actual_product_code
            product.description = description
            product.customs_code = clean_string_field(str(row_data.get(col_map.get('customs_code'), "")))
            product.unit_of_measure = clean_string_field(str(row_data.get(col_map.get('unit_measure'), "")))
            
            # Parse numeric fields
            product.quantity = self._parse_numeric_field(row_data.get(col_map['quantity']))
            product.unit_price = self._parse_numeric_field(row_data.get(col_map['unit_price']))
            product.total_price = self._parse_numeric_field(line_total_val_str)
            
            return product
            
        except Exception as e:
            logger.warning(f"Error extracting product from row {row_index}: {e}")
            return None
    
    def _build_product_description(self, df, row_data, row_index: int, col_map: Dict[str, str], product_lines: List[str]) -> Optional[str]:
        """Build comprehensive product description from multiple sources."""
        
        description_parts = []
        
        # Get description from dedicated column if it exists
        try:
            product_col_index = df.columns.get_loc(col_map['product_code_raw'])
            if product_col_index + 1 < len(df.columns):
                description_col_val = str(row_data[df.columns[product_col_index + 1]]).strip()
                if description_col_val and description_col_val.lower() != 'nan':
                    description_parts.append(description_col_val)
        except (KeyError, IndexError):
            pass
        
        # Add sub-lines from product code cell
        for line_part in product_lines[1:]:
            lp = line_part.strip()
            if lp and lp.lower() != 'nan':
                description_parts.append(lp)
        
        if description_parts:
            return " | ".join(filter(None, description_parts))
        
        return None
    
    def _parse_numeric_field(self, value) -> Optional[str]:
        """Parse and validate numeric fields, return as string for consistency."""
        
        if value is None:
            return None
        
        parsed = parse_italian_decimal(str(value))
        return str(parsed) if parsed is not None else None
    
    def _associate_products_with_deliveries(self, page_data: PageData) -> None:
        """
        Associate products with their respective deliveries based on text position analysis.
        This method analyzes the page text to determine which products belong to which delivery.
        """
        if not page_data.all_deliveries or not page_data.products:
            logger.debug("No deliveries or products found on page - skipping association")
            return
        
        # Clear existing product associations
        for delivery in page_data.all_deliveries:
            delivery.products = []
        
        if len(page_data.all_deliveries) == 1:
            # Simple case: only one delivery, associate all products with it
            page_data.all_deliveries[0].products = page_data.products[:]
            logger.debug(f"Single delivery found - associating all {len(page_data.products)} products with delivery {page_data.all_deliveries[0].ddt_number}")
            return
        
        # Complex case: multiple deliveries, need to determine which products belong to which delivery
        delivery_positions = self._find_delivery_positions_in_text(page_data.raw_text, page_data.all_deliveries)
        product_positions = self._find_product_positions_in_text(page_data.raw_text, page_data.products)
        
        # Associate each product with the delivery that appears before it
        for product, product_pos in zip(page_data.products, product_positions):
            best_delivery = self._find_closest_preceding_delivery(product_pos, delivery_positions, page_data.all_deliveries)
            if best_delivery:
                best_delivery.products.append(product)
                logger.debug(f"Associated product {product.product_code} with delivery {best_delivery.ddt_number}")
            else:
                # Fallback: associate with first delivery
                page_data.all_deliveries[0].products.append(product)
                logger.debug(f"Fallback: Associated product {product.product_code} with first delivery {page_data.all_deliveries[0].ddt_number}")
        
        # Log final association summary
        for delivery in page_data.all_deliveries:
            logger.info(f"Delivery {delivery.ddt_number} has {len(delivery.products)} associated products")
    
    def _find_delivery_positions_in_text(self, page_text: str, deliveries: List[DeliveryData]) -> List[int]:
        """Find the text positions where each delivery appears in the page text."""
        positions = []
        
        for delivery in deliveries:
            # Look for the DDT pattern in the text
            ddt_pattern = f"{delivery.ddt_series}\\s+{delivery.ddt_number}"
            match = re.search(ddt_pattern, page_text)
            if match:
                positions.append(match.start())
            else:
                # Fallback: try to find just the DDT number
                number_pattern = f"\\b{delivery.ddt_number}\\b"
                match = re.search(number_pattern, page_text)
                if match:
                    positions.append(match.start())
                else:
                    # Last resort: use position 0
                    positions.append(0)
                    logger.warning(f"Could not find position for delivery {delivery.ddt_number} in text")
        
        return positions
    
    def _find_product_positions_in_text(self, page_text: str, products: List[ProductData]) -> List[int]:
        """Find the text positions where each product appears in the page text."""
        positions = []
        
        for product in products:
            # Look for the product code in the text
            # Escape special regex characters in product code
            escaped_code = re.escape(product.product_code)
            match = re.search(escaped_code, page_text)
            if match:
                positions.append(match.start())
            else:
                # Fallback: use a large position so it gets associated with the last delivery
                positions.append(len(page_text))
                logger.debug(f"Could not find position for product {product.product_code} in text - using fallback position")
        
        return positions
    
    def _find_closest_preceding_delivery(self, product_position: int, delivery_positions: List[int], deliveries: List[DeliveryData]) -> Optional[DeliveryData]:
        """Find the delivery that appears closest before the given product position."""
        
        best_delivery = None
        best_distance = float('inf')
        
        for i, delivery_pos in enumerate(delivery_positions):
            if delivery_pos <= product_position:  # Delivery must appear before or at the product
                distance = product_position - delivery_pos
                if distance < best_distance:
                    best_distance = distance
                    best_delivery = deliveries[i]
        
        return best_delivery
    
    def _extract_products_from_table(self, df, table_index: int, page_number: int, col_map: Dict[str, str]) -> List[ProductData]:
        """Extract products from a table using proper column mapping."""
        
        products = []
        
        # Skip if table is too small or has no meaningful data
        if len(df) < 2:
            logger.debug(f"Table {table_index + 1} has insufficient rows for product extraction")
            return products
        
        # Try structured extraction first if we have proper column mapping
        if self._validate_required_columns(col_map, table_index, page_number):
            logger.debug(f"Using structured extraction for table {table_index + 1}")
            return self._extract_products_structured(df, table_index, page_number, col_map)
        
        # Fallback to flexible extraction with improved logic
        logger.debug(f"Using flexible extraction for table {table_index + 1}")
        return self._extract_products_flexible(df, table_index, page_number, col_map)
    
    def _extract_products_structured(self, df, table_index: int, page_number: int, col_map: Dict[str, str]) -> List[ProductData]:
        """Extract products using structured column mapping."""
        
        products = []
        
        for row_index in range(1, len(df)):  # Skip header row
            try:
                product = self._extract_product_from_row(df, row_index, col_map)
                if product:
                    products.append(product)
                    logger.debug(f"Structured extraction found product: {product.product_code} - Qty: {product.quantity}, Price: {product.total_price}")
                    
            except Exception as e:
                logger.warning(f"Error extracting product from row {row_index} in table {table_index + 1}: {e}")
                continue
        
        logger.debug(f"Structured extraction found {len(products)} products from table {table_index + 1}")
        return products
    
    def _extract_products_flexible(self, df, table_index: int, page_number: int, col_map: Dict[str, str]) -> List[ProductData]:
        """Extract products using enhanced Camelot+Ghostscript data with proper field parsing."""
        
        products = []
        
        logger.debug(f"Flexible extraction - analyzing table structure:")
        logger.debug(f"Table shape: {df.shape}")
        logger.debug(f"Headers: {df.iloc[0].tolist()}")
        
        # Enhanced row processing to handle Camelot's improved table detection
        for row_index in range(1, len(df)):  # Skip header row
            try:
                row_data = df.iloc[row_index]
                logger.debug(f"Processing row {row_index}: {row_data.tolist()}")
                
                # Step 1: Extract and separate MMA codes from descriptions
                extracted_data = self._parse_row_fields(row_data)
                
                if not extracted_data['has_product_data']:
                    continue
                    
                # Step 2: Extract numeric values from the same row
                numeric_data = self._extract_numeric_from_row(row_data, extracted_data['product_column'])
                
                if not numeric_data['valid']:
                    logger.debug(f"Row {row_index}: Insufficient numeric data")
                    continue
                
                # Step 3: Create product with proper field assignment
                product = ProductData()
                
                # Correct field assignment - MMA codes should be product_code
                if extracted_data['mma_code']:
                    # MMA code found - use as product code
                    product.product_code = extracted_data['mma_code']
                    # If we also found a description, use it, otherwise use the cell content
                    if extracted_data['description']:
                        product.description = extracted_data['description'] 
                    else:
                        # Use the rest of the cell content excluding the MMA code
                        product.description = self._extract_remaining_content_as_description(row_data.iloc[extracted_data['product_column']], extracted_data['mma_code'])
                else:
                    # No MMA code found, use description as product code (fallback)
                    product.product_code = extracted_data['description']
                    product.description = None
                product.quantity = numeric_data['quantity']
                product.unit_price = numeric_data['unit_price'] 
                product.total_price = numeric_data['total_price']
                product.unit_of_measure = self._clean_unit_of_measure(numeric_data['unit_of_measure'])
                
                # Validate the product makes sense
                if self._validate_product_data(product):
                    products.append(product)
                    logger.debug(f"✅ Created product: {product.product_code} | Qty: {product.quantity} | Price: {product.total_price}")
                else:
                    logger.debug(f"❌ Rejected invalid product data for row {row_index}")
                    
            except Exception as e:
                logger.warning(f"Error processing row {row_index}: {e}")
                continue
        
        logger.info(f"Flexible extraction: {len(products)} valid products from table {table_index + 1}")
        return products
    
    def _parse_row_fields(self, row_data) -> Dict[str, Any]:
        """Parse a table row to identify MMA codes, descriptions, and product column."""
        
        result = {
            'mma_code': None,
            'description': None, 
            'product_column': None,
            'has_product_data': False
        }
        
        for col_idx, cell_value in enumerate(row_data):
            cell_str = str(cell_value).strip()
            if not cell_str or cell_str.lower() == 'nan':
                continue
                
            cell_lines = cell_str.split('\n')
            
            # Look for MMA product codes anywhere in the cell
            mma_codes = []
            descriptions = []
            
            for line in cell_lines:
                line = line.strip()
                
                # Check for MMA codes
                if re.match(r'^MMA\d+\.\d+\.\d+', line):
                    mma_codes.append(line)
                
                # Check for Italian product descriptions
                desc_patterns = [
                    r'^Interno adesivo.*',
                    r'^Filo per impunture.*',
                    r'^Etichetta a nr.*',
                    r'^Particolare per confezione.*',
                    r'^Sigillo.*',
                    r'^Tessuto.*',
                    r'^Bottone.*',
                    r'^Materiale da imballo.*'
                ]
                
                for pattern in desc_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        descriptions.append(line)
                        break
            
            # Priority: MMA codes are the real product codes
            if mma_codes:
                result['mma_code'] = mma_codes[0]  # Use first MMA code found
                result['product_column'] = col_idx
                result['has_product_data'] = True
                
                # If we also found descriptions, they go in description field
                if descriptions:
                    result['description'] = descriptions[0]
                    
                logger.debug(f"Found MMA code: {result['mma_code']} in column {col_idx}")
                break
                
            # Fallback: If no MMA code, use description as identifier
            elif descriptions and not result['has_product_data']:
                result['description'] = descriptions[0]
                result['product_column'] = col_idx
                result['has_product_data'] = True
                logger.debug(f"Found description only: {result['description']} in column {col_idx}")
        
        return result
    
    def _extract_remaining_content_as_description(self, cell_content: str, mma_code: str) -> str:
        """Extract non-MMA content from cell as description."""
        try:
            cell_str = str(cell_content).strip()
            lines = cell_str.split('\n')
            
            # Remove the MMA code line and return the rest
            description_parts = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('MMA'):
                    description_parts.append(line)
            
            return ' | '.join(description_parts) if description_parts else None
        except:
            return None
    
    def _extract_numeric_from_row(self, row_data, exclude_column: int) -> Dict[str, Any]:
        """Extract numeric values and unit of measure from a table row."""
        
        result = {
            'quantity': None,
            'unit_price': None, 
            'total_price': None,
            'unit_of_measure': None,
            'valid': False
        }
        
        numeric_values = []
        unit_candidates = []
        
        for col_idx, cell_value in enumerate(row_data):
            if col_idx == exclude_column:  # Skip the product column
                continue
                
            cell_str = str(cell_value).strip()
            if not cell_str or cell_str.lower() == 'nan':
                continue
            
            # Try to parse as numeric value
            parsed_value = self._parse_numeric_field(cell_str)
            if parsed_value and float(parsed_value) > 0:
                numeric_values.append((col_idx, parsed_value))
            
            # Look for unit of measure indicators
            if any(unit in cell_str.upper() for unit in ['MT', 'KG', 'PZ', 'NR', 'KM']):
                unit_candidates.append(cell_str)
        
        # Need at least 3 numeric values for a complete product
        if len(numeric_values) >= 3:
            # Sort by column position (left to right)
            numeric_values.sort(key=lambda x: x[0])
            
            # Assign based on typical Italian invoice structure
            result['quantity'] = numeric_values[-3][1]      # Third from end
            result['unit_price'] = numeric_values[-2][1]    # Second from end
            result['total_price'] = numeric_values[-1][1]   # Last value
            result['valid'] = True
            
            # Use the first valid unit of measure found
            if unit_candidates:
                result['unit_of_measure'] = unit_candidates[0]
                
            logger.debug(f"Numeric extraction: Q={result['quantity']}, P={result['unit_price']}, T={result['total_price']}")
        
        return result
    
    def _clean_unit_of_measure(self, unit_str: str) -> Optional[str]:
        """Clean and standardize unit of measure string."""
        
        if not unit_str:
            return None
            
        # Handle multi-line unit strings (common issue from current extraction)
        lines = str(unit_str).split('\n')
        
        # Look for standard units
        standard_units = ['MT', 'KG', 'PZ', 'NR', 'KM']
        
        for line in lines:
            line = line.strip().upper()
            if line in standard_units:
                return line
                
        # If no standard unit found, return first non-empty line
        for line in lines:
            line = line.strip()
            if line and line.upper() != 'NAN':
                return line[:10]  # Truncate to reasonable length
                
        return None
    
    def _validate_product_data(self, product: ProductData) -> bool:
        """Validate that product data makes sense before adding to results."""
        
        # Must have a product identifier
        if not product.product_code:
            return False
            
        # Must have numeric values
        if not all([product.quantity, product.unit_price, product.total_price]):
            return False
            
        try:
            # Validate mathematical relationship (with tolerance for rounding)
            calc_total = float(product.quantity) * float(product.unit_price)
            actual_total = float(product.total_price)
            diff_percent = abs(calc_total - actual_total) / actual_total * 100
            
            if diff_percent > 5:  # Allow 5% tolerance for rounding differences
                logger.warning(f"Math validation failed: {product.quantity} × {product.unit_price} = {calc_total} ≠ {actual_total}")
                return False
                
            return True
            
        except (ValueError, ZeroDivisionError):
            return False
    
    def _extract_products_from_text(self, raw_text: str) -> List[ProductData]:
        """Extract products from raw text when table extraction fails."""
        
        products = []
        
        try:
            # Look for product code patterns in the text
            # Split text into lines and look for MMA patterns
            lines = raw_text.split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Look for product code patterns
                if re.match(r'^MMA\d+\.\d+\.\d+', line):
                    product = ProductData()
                    product_code_lines = [line]
                    
                    # Look for additional material info on next line
                    if i + 1 < len(lines) and lines[i + 1].strip().startswith('-:'):
                        product_code_lines.append(lines[i + 1].strip())
                        i += 1
                    
                    product.product_code = '\n'.join(product_code_lines)
                    
                    # Look for description in the area around the product code
                    # For this invoice format, descriptions appear in structured blocks
                    description = self._find_description_for_product(lines, i, product.product_code.split('\n')[0])
                    product.description = description
                    
                    # Extract numeric values using a more targeted approach for this invoice format
                    numeric_data = self._extract_numeric_data_for_product(lines, i, product.product_code.split('\n')[0])
                    
                    product.unit_of_measure = numeric_data.get('unit_measure')
                    product.quantity = numeric_data.get('quantity')
                    product.unit_price = numeric_data.get('unit_price')
                    product.total_price = numeric_data.get('total_price')
                    
                    # Only add product if we have at least product code and some numeric data
                    if product.product_code and (product.quantity or product.unit_price or product.total_price):
                        products.append(product)
                        logger.debug(f"Text extraction found product: {product.product_code[:20]}...")
                
                i += 1
            
            logger.info(f"Text-based extraction found {len(products)} products")
            
        except Exception as e:
            logger.error(f"Error in text-based product extraction: {e}")
        
        return products
    
    def _find_description_for_product(self, lines: List[str], product_line_index: int, product_code: str) -> str:
        """Find description for a specific product code in the text."""
        
        # For this specific invoice format, look for description patterns
        # Descriptions like "Interno adesivo - Rinforzo colli" appear near product codes
        description_patterns = [
            r'Interno adesivo.*',
            r'Filo per impunture.*',
            r'Etichetta a nr.*',
            r'Particolare per confezione.*',
            r'Sigillo.*',
            r'Tessuto.*',
            r'Bottone.*',
            r'Materiale da imballo.*',
            r'Passamaneria.*'
        ]
        
        # Search in a window around the product code
        start_line = max(0, product_line_index - 10)
        end_line = min(len(lines), product_line_index + 20)
        
        found_descriptions = []
        
        for i in range(start_line, end_line):
            line = lines[i].strip()
            
            for pattern in description_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    # Check if this description is close to our product code
                    # Look for Alt. (cm) info on the next line
                    desc_parts = [line]
                    if i + 1 < len(lines) and 'Alt. (cm):' in lines[i + 1]:
                        desc_parts.append(lines[i + 1].strip())
                    
                    found_descriptions.append('\n'.join(desc_parts))
                    break
        
        # Return the first relevant description found
        return found_descriptions[0] if found_descriptions else None
    
    def _extract_numeric_data_for_product(self, lines: List[str], product_line_index: int, product_code: str) -> Dict[str, str]:
        """Extract numeric data (quantity, price, total) for a specific product."""
        
        result = {}
        
        # For this invoice format, try to find the row that contains this product's data
        # Look for the pattern: product_code ... numeric_values in nearby lines
        
        # Search in a reasonable window around the product code
        start_line = max(0, product_line_index - 5)
        end_line = min(len(lines), product_line_index + 50)
        
        # Look for unit of measure first
        for k in range(start_line, end_line):
            check_line = lines[k].strip()
            if check_line in ['MT', 'KG', 'NR', 'KM', 'PZ']:
                result['unit_measure'] = check_line
                break
        
        # Collect all numeric values in the area
        numeric_values = []
        for k in range(start_line, end_line):
            check_line = lines[k].strip()
            
            # Look for numeric values with Italian decimal format
            if re.match(r'^\d+[.,]\d+$', check_line):
                try:
                    from ..utils.helpers import parse_italian_decimal
                    parsed = parse_italian_decimal(check_line)
                    if parsed and parsed > 0:
                        numeric_values.append((str(parsed), k))  # Store value and line number
                except:
                    pass
        
        # Try to identify which numbers correspond to quantity, unit_price, total_price
        # Based on the invoice format, look for patterns
        if len(numeric_values) >= 3:
            # Sort by line number to get them in order
            numeric_values.sort(key=lambda x: x[1])
            
            # For this invoice format, typically:
            # - quantity appears first
            # - unit_price appears second 
            # - total_price appears last
            result['quantity'] = numeric_values[0][0]
            result['unit_price'] = numeric_values[1][0]
            result['total_price'] = numeric_values[-1][0]
            
        elif len(numeric_values) >= 2:
            result['unit_price'] = numeric_values[0][0]
            result['total_price'] = numeric_values[1][0]
            
        elif len(numeric_values) >= 1:
            result['total_price'] = numeric_values[0][0]
        
        return result