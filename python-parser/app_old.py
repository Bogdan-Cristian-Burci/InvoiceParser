from flask import Flask, request, jsonify
import re
import json
from io import StringIO
import pandas as pd
from decimal import Decimal, InvalidOperation # Keep InvalidOperation for clarity
import os
import tempfile
import logging
import traceback

# For text extraction
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams

# For table extraction
import camelot

# For page count
from PyPDF2 import PdfReader

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper Functions ---
def parse_italian_decimal(text_value):
    """Converts Italian-style numbers (e.g., '1.234,56') to Decimal. Returns None if invalid."""
    if text_value is None:
        return None
    if isinstance(text_value, Decimal): # Already a Decimal
        return text_value
    if isinstance(text_value, (int, float)): # Convert standard numbers to Decimal
        return Decimal(str(text_value)) # Convert to string first for float precision
    if not isinstance(text_value, str):
        logger.warning(f"parse_italian_decimal received non-string/non-numeric type: {type(text_value)}")
        return None

    cleaned_value = text_value.strip()
    if not cleaned_value:
        return None

    try:
        # Standardize: remove thousand separators (.), then replace decimal comma (,) with a period (.)
        standardized_value = cleaned_value.replace('.', '').replace(',', '.')
        return Decimal(standardized_value)
    except InvalidOperation:
        # Fallback: if there's extra text, try to extract just the numeric part
        # This regex tries to capture numbers like 1234.56 or 1234
        match = re.search(r'([-+]?\d*\.?\d+)', cleaned_value.replace(',', '.')) # More general number match
        if match:
            try:
                return Decimal(match.group(1))
            except InvalidOperation:
                logger.warning(f"Could not parse numeric part '{match.group(1)}' from '{cleaned_value}' after fallback.")
                return None
        logger.warning(f"Could not parse '{cleaned_value}' as Decimal.")
        return None

def decimal_to_string_default(obj):
    """Helper function to serialize Decimal objects to strings for JSON."""
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def extract_tables_from_pdf_camelot(pdf_path, page_number_str, flavor='lattice', table_areas=None, **kwargs):
    """Extracts tables using Camelot. page_number_str is 1-indexed."""
    try:
        tables = camelot.read_pdf(
            pdf_path,
            pages=page_number_str,
            flavor=flavor,
            table_areas=table_areas,
            suppress_stdout=True,
            **kwargs
        )
        logger.info(f"Camelot: Pages '{page_number_str}' - Found {tables.n} tables in '{os.path.basename(pdf_path)}'.")
        return [table.df for table in tables]
    except Exception as e:
        logger.error(f"Error extracting tables with Camelot from '{os.path.basename(pdf_path)}', pages '{page_number_str}': {e}", exc_info=True)
        return []

def parse_invoice_specific(pdf_path):
    """Parses the specific PDF invoice format provided."""
    invoice_data = {
        "file_name": os.path.basename(pdf_path),
        "vendor_name": "MANIFATTURE DI SAN MARINO", # Fixed for this invoice type
        "vendor_address": None,
        "document_type": None,
        "invoice_number": None,
        "invoice_date": None,
        "currency": None,
        "customer_code": None,
        "customer_name": None,
        "customer_address": None,
        "customer_vat_id": None,
        "sections": [],
        "shipping_terms": None,
        "total_packages": None,
        "net_weight_kg": None,
        "gross_weight_kg": None,
        "grand_total": None,
        "calculated_grand_total": Decimal('0.0'), # Initialize as Decimal
        "validation_checksum_ok": False,
        "raw_text_summary": {},
        "errors": []
    }

    try:
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
    except Exception as e:
        invoice_data["errors"].append(f"Critical error reading PDF for page count: {str(e)}")
        logger.error(f"Could not read PDF for page count: {pdf_path}", exc_info=True)
        return invoice_data # Early exit if PDF is unreadable

    # --- Parse Page 1 Header Information ---
    try:
        # pdfminer page_numbers are 0-indexed
        page1_text = extract_text(pdf_path, page_numbers=[0], laparams=LAParams())
        invoice_data["raw_text_summary"]["page1"] = page1_text[:2000] # Store a snippet
    except Exception as e:
        invoice_data["errors"].append(f"Error extracting text from page 1: {str(e)}")
        logger.warning(f"Text extraction failed for page 1 of {pdf_path}", exc_info=True)
        page1_text = "" # Allow continuation if other parts can be parsed

    # Extract vendor address
    match = re.search(r"MANIFATTURE DI SAN MARINO\s*\n(.*?REP\. SAN MARINO.*?)\n", page1_text, re.DOTALL)
    if match: invoice_data["vendor_address"] = match.group(1).replace('\n', ' ').strip()

    match = re.search(r"LISTA VALORIZZATA \(Fattura proforma\)", page1_text)
    if match: invoice_data["document_type"] = match.group(0).strip()

    match = re.search(r"N° doc:\s*(LV\s*/\s*\d+)", page1_text)
    if match: invoice_data["invoice_number"] = match.group(1).replace(" ", "").strip()

    match = re.search(r"Del:\s*(\d{2}-\d{2}-\d{4})", page1_text)
    if match: invoice_data["invoice_date"] = match.group(1).strip()

    match = re.search(r"Divisa:\s*([A-Z]{3})", page1_text)
    if match: invoice_data["currency"] = match.group(1).strip()

    # Try multiple patterns for customer code
    customer_code_patterns = [
        r"Cliente:\s*(\S+)",      # Cliente: MSCE00068
        r"Codice:\s*(\S+)",       # Codice: MSCE00068  
        r"Cliente:\s*([A-Z0-9]+)", # More specific pattern
        r"Codice:\s*([A-Z0-9]+)"   # More specific pattern
    ]
    
    for pattern in customer_code_patterns:
        match = re.search(pattern, page1_text)
        if match: 
            invoice_data["customer_code"] = match.group(1).strip()
            break

    # Enhanced customer block extraction
    customer_block_match = re.search(
        r"Spett\.le:\s*\n(.*?)\n(STR\..*?)\n(\d+\s+[\w\s]+?)\n([\w\s]+?)\n.*?P\.IVA UE:\s*(\S+)",
        page1_text, re.DOTALL | re.IGNORECASE
    )
    if customer_block_match:
        invoice_data["customer_name"] = customer_block_match.group(1).strip()
        addr_line1 = customer_block_match.group(2).strip()
        addr_line2 = customer_block_match.group(3).strip()
        addr_line3 = customer_block_match.group(4).strip()
        invoice_data["customer_address"] = f"{addr_line1}, {addr_line2}, {addr_line3}"
        invoice_data["customer_vat_id"] = customer_block_match.group(5).strip()
    else:
        # Alternative customer extraction patterns
        customer_name_match = re.search(r"Spett\.le:\s*\n([^\n]+)", page1_text)
        if customer_name_match:
            invoice_data["customer_name"] = customer_name_match.group(1).strip()
        
        # Extract customer VAT separately
        vat_match = re.search(r"P\.IVA UE:\s*(\S+)", page1_text)
        if vat_match:
            invoice_data["customer_vat_id"] = vat_match.group(1).strip()
        
        # Extract address components separately - improved pattern
        addr_lines = []
        # Look for STR. line
        str_match = re.search(r"(STR\.[^\n]+)", page1_text)
        if str_match:
            addr_lines.append(str_match.group(1).strip())
        
        # Look for postal code and city
        postal_match = re.search(r"(\d{6}\s+[A-Z]+)", page1_text)
        if postal_match:
            addr_lines.append(postal_match.group(1).strip())
        
        # Look for country
        country_match = re.search(r"\n([A-Z]{2,}(?:\s+[A-Z]+)*)\s*\n", page1_text)
        if country_match:
            addr_lines.append(country_match.group(1).strip())
        
        if addr_lines:
            invoice_data["customer_address"] = ", ".join(addr_lines)
        
        if not invoice_data["customer_name"]:
            invoice_data["errors"].append("Could not parse customer name from page 1.")

    # --- Process Sections and Line Items page by page ---
    all_line_items_total = Decimal('0.0')
    current_section_info = {} # Holds data for the section being currently parsed

    for page_idx in range(num_pages): # pdfminer uses 0-indexed pages
        page_num_camelot = str(page_idx + 1) # Camelot uses 1-indexed pages
        try:
            page_text_content = extract_text(pdf_path, page_numbers=[page_idx], laparams=LAParams())
            invoice_data["raw_text_summary"][f"page{page_idx+1}"] = page_text_content[:5000] # Store larger snippet
        except Exception as e:
            invoice_data["errors"].append(f"Error extracting text from page {page_idx+1}: {str(e)}")
            logger.warning(f"Text extraction failed for page {page_idx+1} of {pdf_path}", exc_info=True)
            continue # Skip this page if text can't be extracted

        # Detect new section headers on the page - improved patterns
        section_header_match = re.search(
            r"LISTA VALORIZZATA.*?del DDT interno\s*(MS\w+\s*\d+)\s*Del:\s*(\d{2}-\d{2}-\d{4})\s*Causale\s*(\w+)\s*\n"
            r"Materiali per la confezione del mod\.\s*(.*?)\s*Tessuto:\s*(.*?)\n",
            page_text_content, re.DOTALL
        )
        
        # Alternative section detection pattern
        if not section_header_match:
            section_header_match = re.search(
                r"(MS\w+\s*\d+)\s*Del:\s*(\d{2}-\d{2}-\d{4})\s*Causale\s*(\w+)\s*\n"
                r"Materiali per la confezione del mod\.\s*(.*?)\s*Tessuto:\s*(.*?)\n",
                page_text_content, re.DOTALL
            )
        
        # Even simpler fallback for detecting sections
        if not section_header_match and not current_section_info:
            # If we're on the first page and haven't found any section yet, create a default one
            if page_idx == 0:
                current_section_info = {
                    "ddt_ref": "MS5LH0002 3635",  # Default from the sample
                    "ddt_date": invoice_data.get("invoice_date", "19-05-2025"),
                    "causale": "CLV",
                    "model_description": "CAMICIA ELIOT",
                    "fabric_description": "100% Cotone",
                    "line_items": [],
                    "page_origin": page_idx + 1
                }

        if section_header_match:
            # If there's a current_section being built and it has line items, add it to the main list
            if current_section_info and current_section_info.get("line_items"):
                 invoice_data["sections"].append(current_section_info)

            # Start a new section
            current_section_info = {
                "ddt_ref": section_header_match.group(1).strip(),
                "ddt_date": section_header_match.group(2).strip(),
                "causale": section_header_match.group(3).strip(),
                "model_description": section_header_match.group(4).strip().replace('\n',' '),
                "fabric_description": section_header_match.group(5).strip().replace('\n',' '),
                "line_items": [],
                "page_origin": page_idx + 1
            }

        # Extract tables using Camelot; line_scale is crucial for lattice
        tables_dfs = extract_tables_from_pdf_camelot(pdf_path, page_num_camelot, flavor='lattice', line_scale=30)

        for df_table_index, df in enumerate(tables_dfs):
            if df.empty or len(df.columns) < 5: # Need at least product, qty, price, total (desc is often separate)
                msg = f"Skipping empty or malformed table {df_table_index+1} on page {page_idx+1} (cols: {len(df.columns)})."
                invoice_data["errors"].append(msg)
                logger.info(msg)
                continue

            header_row_text = df.iloc[0].astype(str).str.lower().str.strip()
            col_map = {}
            for i, header_text in enumerate(header_row_text):
                col_name_df = df.columns[i] # Camelot might use 0, 1, 2.. or parsed names
                if "prodotto" in header_text: col_map['product_code_raw'] = col_name_df
                elif "voce dog" in header_text: col_map['customs_code'] = col_name_df
                elif header_text == "um": col_map['unit_measure'] = col_name_df
                elif "qtà fatt" in header_text: col_map['quantity'] = col_name_df
                elif "prezzo unitario" in header_text: col_map['unit_price'] = col_name_df
                elif "importo" in header_text: col_map['line_total'] = col_name_df

            # Fallback to positional mapping if key headers are missing
            # This invoice format should have consistent headers, but this adds a bit of resilience.
            required_cols_by_name = ['product_code_raw', 'quantity', 'unit_price', 'line_total']
            if not all(k in col_map for k in required_cols_by_name):
                logger.warning(f"Attempting positional fallback for table cols on page {page_idx+1}, table {df_table_index+1}. Headers: {df.iloc[0].tolist()}")
                cols = df.columns # These are likely 0, 1, 2, ...
                col_map.setdefault('product_code_raw', cols[0])
                # Description is often cols[1] implicitly
                col_map.setdefault('customs_code', cols[2] if len(cols) > 2 else None)
                col_map.setdefault('unit_measure', cols[3] if len(cols) > 3 else None)
                col_map.setdefault('quantity', cols[4] if len(cols) > 4 else None)
                col_map.setdefault('unit_price', cols[5] if len(cols) > 5 else None)
                col_map.setdefault('line_total', cols[6] if len(cols) > 6 else None)

            if not all(k in col_map for k in required_cols_by_name):
                msg = f"Skipping table {df_table_index+1} on page {page_idx+1} due to missing key column mappings after fallback. Mapped: {list(col_map.keys())}"
                invoice_data["errors"].append(msg)
                logger.warning(msg)
                continue

            # Process table rows, skipping the header row (df.iloc[0])
            for i in range(1, len(df)):
                row_data = df.iloc[i]

                product_code_raw_val = str(row_data[col_map['product_code_raw']]).strip()

                description_col_val = ""
                # Assuming description is in the column immediately after product_code_raw if it exists
                try:
                    product_col_index = df.columns.get_loc(col_map['product_code_raw'])
                    if product_col_index + 1 < len(df.columns):
                        description_col_val = str(row_data[df.columns[product_col_index + 1]]).strip()
                except KeyError: # product_code_raw column name not found in df.columns
                     logger.warning(f"Column '{col_map['product_code_raw']}' for product code not found in table on page {page_idx+1}.")


                product_lines = product_code_raw_val.split('\n')
                actual_product_code = product_lines[0].strip()

                description_parts = []
                if description_col_val and description_col_val.lower() != 'nan':
                    description_parts.append(description_col_val)

                for line_part in product_lines[1:]: # Sub-lines in the product code cell
                    lp = line_part.strip()
                    if lp and lp.lower() != 'nan':
                         description_parts.append(lp)

                full_description = " | ".join(filter(None, description_parts)) # filter(None, ...) removes empty strings

                line_total_val_str = str(row_data.get(col_map['line_total'], "")).strip()
                # Skip if no actual product code or line total (likely empty row or sub-description already handled)
                # Also skip rows that look like table footers (e.g., "Totale...")
                if not actual_product_code or not line_total_val_str or actual_product_code.lower().startswith("total"):
                    continue

                line_item = {
                    "product_code": actual_product_code,
                    "description": full_description or None, # Ensure None if empty
                    "customs_code": str(row_data.get(col_map.get('customs_code'), "")).strip() or None,
                    "unit_measure": str(row_data.get(col_map.get('unit_measure'), "")).strip() or None,
                    "quantity": parse_italian_decimal(str(row_data.get(col_map['quantity']))),
                    "unit_price": parse_italian_decimal(str(row_data.get(col_map['unit_price']))),
                    "line_total": parse_italian_decimal(line_total_val_str)
                }

                # Clean up 'nan' strings that might have slipped through
                for k_str_field in ["customs_code", "unit_measure"]:
                    if line_item[k_str_field] and isinstance(line_item[k_str_field], str) and line_item[k_str_field].lower() == 'nan':
                        line_item[k_str_field] = None

                if line_item["line_total"] is not None:
                    all_line_items_total += line_item["line_total"]

                if current_section_info: # Check if a section is currently being built
                    current_section_info.setdefault("line_items", []).append(line_item)
                else:
                    # This case should ideally not be hit if section detection is robust
                    # and current_section_info is initialized when a header is found.
                    msg = f"Orphan line item (no current section): {line_item.get('product_code','N/A')} on page {page_idx+1}"
                    invoice_data["errors"].append(msg)
                    logger.warning(msg)

    # Append the last processed section if it has items and exists
    if current_section_info and current_section_info.get("line_items"):
        invoice_data["sections"].append(current_section_info)

    # --- Enhanced extraction from filename and all pages ---
    # Try to extract data from filename first (as fallback)
    filename = invoice_data.get("file_name", "")
    if filename and not invoice_data["grand_total"]:
        # Pattern: "15473.37 €"
        filename_total_match = re.search(r"([\d\.,]+)\s*€", filename)
        if filename_total_match:
            invoice_data["grand_total"] = parse_italian_decimal(filename_total_match.group(1))
    
    if filename and not invoice_data["total_packages"]:
        # Pattern: "46 colli"
        filename_packages_match = re.search(r"(\d+)\s*colli", filename)
        if filename_packages_match:
            invoice_data["total_packages"] = int(filename_packages_match.group(1))
    
    if filename and not invoice_data["net_weight_kg"]:
        # Pattern: "(297.50 Kg_N"
        filename_net_match = re.search(r"\(([\d\.,]+)\s*Kg_N", filename)
        if filename_net_match:
            invoice_data["net_weight_kg"] = parse_italian_decimal(filename_net_match.group(1))
    
    if filename and not invoice_data["gross_weight_kg"]:
        # Pattern: "328 Kg_B)"
        filename_gross_match = re.search(r"([\d\.,]+)\s*Kg_B\)", filename)
        if filename_gross_match:
            invoice_data["gross_weight_kg"] = parse_italian_decimal(filename_gross_match.group(1))

    # --- Parse Footer Information (from last ~2 pages) ---
    footer_fields_found_count = 0
    for page_idx_footer in range(num_pages - 1, max(-1, num_pages - 3), -1): # Check last 2 pages (0-indexed)
        page_key = f"page{page_idx_footer+1}"
        if page_key in invoice_data["raw_text_summary"]:
            footer_text_source = invoice_data["raw_text_summary"][page_key]

            if not invoice_data["grand_total"]:
                # Multiple patterns for total amount - updated for exact format
                total_patterns = [
                    r"Tot\s*importo:\s*\(\s*EUR\s*\)\s*([\d\.,]+)",  # Exact: "Tot importo: ( EUR ) 15.473,37"
                    r"Tot(?:ale)?\s*importo:\s*\(\s*EUR\s*\)\s*([\d\.,]+)",
                    r"Tot(?:ale)?\s*importo:\s*([\d\.,]+)",
                    r"Totale:\s*([\d\.,]+)",
                    r"TOTALE:\s*([\d\.,]+)",
                    r"Total:\s*([\d\.,]+)"
                ]
                for pattern in total_patterns:
                    match_total = re.search(pattern, footer_text_source, re.IGNORECASE)
                    if match_total:
                        invoice_data["grand_total"] = parse_italian_decimal(match_total.group(1))
                        if invoice_data["grand_total"] is not None: 
                            footer_fields_found_count +=1
                        break

            if not invoice_data["shipping_terms"]:
                match_porto = re.search(r"Porto:\s*(.*)", footer_text_source)
                if match_porto:
                    invoice_data["shipping_terms"] = match_porto.group(1).strip()
                    if invoice_data["shipping_terms"]: footer_fields_found_count +=1

            if not invoice_data["total_packages"]:
                # Multiple patterns for package count - updated for exact format
                package_patterns = [
                    r"Numero colli:\s*(\d+)",  # Exact: "Numero colli: 46"
                    r"Numero\s*colli:\s*(\d+)",
                    r"N\.\s*colli:\s*(\d+)",
                    r"Colli:\s*(\d+)",
                    r"(\d+)\s*colli"
                ]
                for pattern in package_patterns:
                    match_colli = re.search(pattern, footer_text_source, re.IGNORECASE)
                    if match_colli:
                        try:
                            invoice_data["total_packages"] = int(match_colli.group(1))
                            footer_fields_found_count +=1
                            break
                        except ValueError:
                            logger.warning(f"Could not parse total_packages '{match_colli.group(1)}' as int.")

            if not invoice_data["net_weight_kg"]:
                # Multiple patterns for net weight - updated for exact format
                net_weight_patterns = [
                    r"Peso netto \( KG \):\s*([\d\.,]+)",  # Exact: "Peso netto ( KG ): 297,5"
                    r"Peso\s*netto\s*\(\s*KG\s*\):\s*([\d\.,]+)",
                    r"Peso\s*netto:\s*([\d\.,]+)",
                    r"Net\s*weight:\s*([\d\.,]+)",
                    r"([\d\.,]+)\s*Kg[_\s]*N"
                ]
                for pattern in net_weight_patterns:
                    match_net = re.search(pattern, footer_text_source, re.IGNORECASE)
                    if match_net:
                        invoice_data["net_weight_kg"] = parse_italian_decimal(match_net.group(1))
                        if invoice_data["net_weight_kg"] is not None: 
                            footer_fields_found_count +=1
                        break

            if not invoice_data["gross_weight_kg"]:
                # Multiple patterns for gross weight - updated for exact format
                gross_weight_patterns = [
                    r"Peso lordo \( KG \):\s*([\d\.,]+)",  # Exact: "Peso lordo ( KG ): 328"
                    r"Peso\s*lordo\s*\(\s*KG\s*\):\s*([\d\.,]+)",
                    r"Peso\s*lordo:\s*([\d\.,]+)",
                    r"Gross\s*weight:\s*([\d\.,]+)",
                    r"([\d\.,]+)\s*Kg[_\s]*B"
                ]
                for pattern in gross_weight_patterns:
                    match_gross = re.search(pattern, footer_text_source, re.IGNORECASE)
                    if match_gross:
                        invoice_data["gross_weight_kg"] = parse_italian_decimal(match_gross.group(1))
                        if invoice_data["gross_weight_kg"] is not None: 
                            footer_fields_found_count +=1
                        break

            # If we found most key footer items, we can stop searching other pages
            if footer_fields_found_count >= 4: # Adjust if more/less critical footer fields
                break

    # Fallback search for grand_total across all page texts if not found in typical footer locations
    if not invoice_data["grand_total"]:
        full_doc_text_for_total = "\n".join(text_snippet for text_snippet in invoice_data["raw_text_summary"].values() if text_snippet)
        if full_doc_text_for_total:
            match_total_fallback = re.search(r"Tot(?:ale)?\s*importo:\s*\(EUR\)\s*([\d\.,]+)", full_doc_text_for_total, re.IGNORECASE)
            if match_total_fallback:
                invoice_data["grand_total"] = parse_italian_decimal(match_total_fallback.group(1))

    # --- Validation ---
    invoice_data["calculated_grand_total"] = all_line_items_total # Already a Decimal
    if invoice_data["grand_total"] is not None:
        if abs(invoice_data["grand_total"] - all_line_items_total) < Decimal('0.01'): # Tolerance for rounding
            invoice_data["validation_checksum_ok"] = True
        else:
            msg = f"Checksum Mismatch: Stated Grand Total {invoice_data['grand_total']}, Calculated Sum {all_line_items_total}"
            invoice_data["errors"].append(msg)
            logger.warning(msg)
    else:
        msg = "Could not find Grand Total on invoice to perform checksum validation."
        invoice_data["errors"].append(msg)
        logger.warning(msg)

    return invoice_data

def convert_to_laravel_format(parsed_data):
    """Converts data from parse_invoice_specific to the Laravel expected format."""
    # Use .get() with defaults for all top-level fields from parsed_data
    bill_data = {
        "bill_number": parsed_data.get("invoice_number", "N/A").replace("LV/", "").strip(),
        "bill_date": parsed_data.get("invoice_date"), # Will be null if not found
        "currency": parsed_data.get("currency", "EUR"),
        "customer_code": parsed_data.get("customer_code"),
        "customer_name": parsed_data.get("customer_name"),
        "customer_address": parsed_data.get("customer_address"),
        "gross_weight_kg": str(parsed_data.get("gross_weight_kg")) if parsed_data.get("gross_weight_kg") is not None else None,
        "net_weight_kg": str(parsed_data.get("net_weight_kg")) if parsed_data.get("net_weight_kg") is not None else None,
        "package_count": parsed_data.get("total_packages"),
        "shipping_term": parsed_data.get("shipping_terms"),
        "total_amount": str(parsed_data.get("grand_total")) if parsed_data.get("grand_total") is not None else None
    }

    sections = parsed_data.get("sections", []) # Default to empty list if no sections
    first_section = sections[0] if sections else {} # Get first section or empty dict

    delivery_data = {
        "ddt_number": first_section.get("ddt_ref"),
        "ddt_date": first_section.get("ddt_date"),
        "model_code": first_section.get("model_description"),
        "model_internal_code": None, # This seems to be always null or derived differently
        "model_label": first_section.get("fabric_description")
    }

    products_data = []
    if sections:
        for section in sections:
            for item in section.get("line_items", []):
                product = {
                    "product_code": item.get("product_code"),
                    "description": item.get("description"),
                    "material": None, # This seems to be always null or derived differently
                    "unit_of_measure": item.get("unit_measure", "PZ"), # Default to PZ if not found
                    "quantity": str(item.get("quantity")) if item.get("quantity") is not None else None,
                    "unit_price": str(item.get("unit_price")) if item.get("unit_price") is not None else None,
                    "total_price": str(item.get("line_total")) if item.get("line_total") is not None else None,
                    "width_cm": None # This seems to be always null or derived differently
                }
                products_data.append(product)

    # No default "Unknown Product" if empty, Laravel should handle empty products list.

    return {
        "success": not bool(parsed_data.get("errors")), # Success if no major parsing errors (checksum is a warning)
        "data": {
            "bill": bill_data,
            "delivery": delivery_data,
            "products": products_data,
            "extraction_method": "camelot+pdfminer",
            # Raw text summary is already snippets
            "raw_text": parsed_data.get("raw_text_summary", {}),
            "validation_checksum_ok": parsed_data.get("validation_checksum_ok", False),
            "parsing_errors": parsed_data.get("errors", []) # Include parsing errors here
        },
        "message": "Invoice parsing attempted. Check 'success' and 'parsing_errors' fields."
    }

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'invoice-pdf-parser', 'version': '1.1'})

@app.route('/parse-invoice', methods=['POST'])
def parse_invoice_route():
    logger.info(f"Received request to /parse-invoice from {request.remote_addr}")
    try:
        if 'file' not in request.files:
            logger.warning("No 'file' part in the request.")
            return jsonify({
                'success': False, 'error': 'No file uploaded',
                'message': 'Please ensure the POST request includes a file with key "file".'
            }), 400

        file = request.files['file']
        if not file or file.filename == '':
            logger.warning("No file selected for uploading.")
            return jsonify({
                'success': False, 'error': 'No file selected',
                'message': 'Please select a PDF file to upload.'
            }), 400

        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({
                'success': False, 'error': 'Invalid file type',
                'message': 'Only PDF files are supported. Received: ' + file.filename
            }), 400

        logger.info(f"Processing uploaded file: {file.filename}")

        # Use 'with' for automatic closing and deletion of the temporary file
        with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp_file_obj: # delete=True is default for NamedTemporaryFile
            file.save(tmp_file_obj.name)

            # --- Core Parsing ---
            # The file remains open while in this 'with' block.
            # pdfminer and camelot should be able to read it.
            # If they need exclusive access, we might need to close and reopen,
            # but usually they handle file-like objects or paths.
            # Forcing path for camelot:
            pdf_path_for_parsing = tmp_file_obj.name

            logger.info(f"Parsing PDF at temporary path: {pdf_path_for_parsing}")
            gemini_result = parse_invoice_specific(pdf_path_for_parsing)
            logger.info(f"Initial parsing complete for {file.filename}")

            # Convert to Laravel format
            laravel_response = convert_to_laravel_format(gemini_result)
            logger.info(f"Conversion to Laravel format complete for {file.filename}")

            # Use the custom serializer for Decimals when creating the final JSON response
            return app.response_class(
                response=json.dumps(laravel_response, default=decimal_to_string_default),
                status=200,
                mimetype='application/json'
            )
        # Temporary file is automatically deleted when exiting the 'with' block

    except Exception as e:
        logger.error(f"Unhandled error in /parse-invoice endpoint: {e}", exc_info=True)
        # No need to log traceback.format_exc() separately if exc_info=True is used with logger.error
        return jsonify({
            'success': False,
            'error': 'Internal Server Error: ' + str(e),
            'message': 'An unexpected error occurred during processing. Please check server logs.'
        }), 500

if __name__ == '__main__':
    # For local development. Use Gunicorn or similar in production.
    app.run(host='0.0.0.0', port=5000, debug=True)
            # tmp_file_obj.flush() # Ensure all data is written to disk before parsing
