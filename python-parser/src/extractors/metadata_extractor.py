import re
import os
import logging
from typing import Optional
from ..models.invoice_models import BillData
from ..utils.pdf_utils import extract_text_from_page, get_pdf_page_count
from ..utils.helpers import parse_italian_decimal, extract_numeric_from_filename, format_address_lines

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts general invoice metadata from PDF header and filename."""
    
    def __init__(self):
        self.vendor_name = "MANIFATTURE DI SAN MARINO"  # Fixed for this invoice type
    
    def extract_general_metadata(self, pdf_path: str) -> BillData:
        """
        Extract general bill/invoice metadata from the PDF.
        This focuses on header information that appears on page 1.
        """
        bill_data = BillData()
        bill_data.customer_address = None
        
        # Set filename for potential fallback extraction
        filename = os.path.basename(pdf_path)
        
        # Verify PDF is readable
        page_count = get_pdf_page_count(pdf_path)
        if page_count == 0:
            logger.error(f"Cannot read PDF for metadata extraction: {pdf_path}")
            return bill_data
        
        # Extract text from first page for header information
        page1_text = extract_text_from_page(pdf_path, 0)
        if not page1_text:
            logger.warning(f"Could not extract text from page 1 of {pdf_path}")
            # Try filename extraction as fallback
            return self._extract_from_filename(filename, bill_data)
        
        # Extract header fields
        self._extract_invoice_header(page1_text, bill_data)
        self._extract_customer_info(page1_text, bill_data)
        
        # Apply data validation and fix common mapping issues
        self._fix_data_mapping_issues(bill_data)
        
        # Fallback to filename extraction for missing critical fields
        self._extract_missing_from_filename(filename, bill_data)
        
        return bill_data
    
    def _extract_invoice_header(self, page_text: str, bill_data: BillData) -> None:
        """Extract invoice header information (number, date, currency, etc.)."""
        
        # Log first 1000 chars of text being processed for debugging
        logger.info(f"Processing page text for customer_code extraction (first 1000 chars):\n{page_text[:1000]}")
        
        # Document type
        match = re.search(r"LISTA VALORIZZATA \(Fattura proforma\)", page_text)
        if match:
            # This is implicit - we know it's a proforma invoice
            pass
        
        # Invoice number - pattern: "N° doc: LV / 502"
        match = re.search(r"N° doc:\s*(LV\s*/\s*\d+)", page_text)
        if match:
            bill_data.bill_number = match.group(1).replace(" ", "").replace("LV/", "").strip()
        
        # Invoice date - pattern: "Del: 19-05-2025"
        match = re.search(r"Del:\s*(\d{2}-\d{2}-\d{4})", page_text)
        if match:
            bill_data.bill_date = match.group(1).strip()
        
        # Enhanced patterns for combined Divisa/Cliente format
        combined_patterns = [
            r"Divisa:\s*Cliente:\s*([A-Z]{3})\s+([A-Z0-9]+)",  # "Divisa: Cliente: EUR MSCE00068"
            r"Divisa:\s*([A-Z]{3})\s*Cliente:\s*([A-Z0-9]+)",  # Alternative order
        ]
        
        # Try combined pattern first
        combined_match_found = False
        for pattern in combined_patterns:
            match = re.search(pattern, page_text)
            if match:
                bill_data.currency = match.group(1).strip()
                bill_data.customer_code = match.group(2).strip()
                logger.info(f"Combined pattern matched - Currency: {bill_data.currency}, Customer: {bill_data.customer_code}")
                combined_match_found = True
                break
        
        # Fallback to individual patterns if combined didn't match
        if not combined_match_found:
            # Currency - pattern: "Divisa: EUR"
            if not bill_data.currency:
                match = re.search(r"Divisa:\s*([A-Z]{3})", page_text)
                if match:
                    bill_data.currency = match.group(1).strip()
            
            # Customer code - multiple patterns to try
            if not bill_data.customer_code:
                customer_code_patterns = [
                    r"Cliente:\s*(\w+)",           # Cliente: MSCE00068
                    r"Codice:\s*(\w+)",            # Codice: MSCE00068  
                    r"Cliente:\s*([A-Z0-9]+)",     # More specific pattern
                    r"Codice:\s*([A-Z0-9]+)"       # More specific pattern
                ]
                
                logger.info(f"Searching for customer_code patterns...")
                for i, pattern in enumerate(customer_code_patterns):
                    match = re.search(pattern, page_text)
                    logger.info(f"Pattern {i+1}: {pattern} -> {'Found: ' + match.group(1) if match else 'No match'}")
                    if match and match.group(1) != bill_data.currency:  # Avoid currency/code confusion
                        bill_data.customer_code = match.group(1).strip()
                        logger.info(f"Customer code set to: {bill_data.customer_code}")
                        break
        
        if not bill_data.customer_code:
            logger.warning("No customer_code found with any pattern")
    
    def _extract_customer_info(self, page_text: str, bill_data: BillData) -> None:
        """Extract customer information (name, address, VAT)."""
        
        # Try comprehensive customer block extraction first
        # P.IVA UE appears BEFORE Spett.le, so pattern needs to account for that
        customer_block_match = re.search(
            r"P\.IVA UE:\s*(\S+).*?Spett\.le:\s*\n([^\n]+)\n(STR\.[^\n]+)\n(\d{6}\s+[A-Z]+)\n([A-Z]+)",
            page_text, re.DOTALL | re.IGNORECASE
        )
        
        if customer_block_match:
            bill_data.customer_vat_id = customer_block_match.group(1).strip()
            bill_data.customer_name = customer_block_match.group(2).strip()
            addr_line1 = customer_block_match.group(3).strip()
            addr_line2 = customer_block_match.group(4).strip()
            addr_line3 = customer_block_match.group(5).strip()
            bill_data.customer_address = format_address_lines([addr_line1, addr_line2, addr_line3])
        else:
            # Fallback to individual field extraction
            self._extract_customer_fields_individually(page_text, bill_data)
    
    def _extract_customer_fields_individually(self, page_text: str, bill_data: BillData) -> None:
        """Extract customer fields individually when block extraction fails."""
        
        # Customer name - pattern: "Spett.le: S.C. TEXBRA SRL"
        customer_name_match = re.search(r"Spett\.le:\s*\n([^\n]+)", page_text)
        if customer_name_match:
            bill_data.customer_name = customer_name_match.group(1).strip()
        
        # Customer VAT - pattern: "P.IVA UE: RO17378052"
        vat_match = re.search(r"P\.IVA UE:\s*(\S+)", page_text)
        if vat_match:
            bill_data.customer_vat_id = vat_match.group(1).strip()
        
        # Address components - extract in sequence after "Spett.le:"
        addr_lines = []
        
        # First, find the customer section to extract address from the right context
        # Note: P.IVA UE appears BEFORE Spett.le, so we look for the section after Spett.le until LISTA
        spett_match = re.search(r"Spett\.le:\s*\n([^\n]+)\n(.*?)(?=LISTA VALORIZZATA)", page_text, re.DOTALL)
        if spett_match:
            customer_section = spett_match.group(2)
            
            # Street address - pattern: "STR. VADENI 16"
            str_match = re.search(r"(STR\.[^\n]+)", customer_section)
            if str_match:
                addr_lines.append(str_match.group(1).strip())
            
            # Postal code and city - pattern: "810176 BRAILA"
            postal_match = re.search(r"(\d{6}\s+[A-Z]+)", customer_section)
            if postal_match:
                addr_lines.append(postal_match.group(1).strip())
            
            # Country - pattern: "ROMANIA"
            country_match = re.search(r"^([A-Z]{2,}(?:\s+[A-Z]+)*)$", customer_section, re.MULTILINE)
            if country_match:
                addr_lines.append(country_match.group(1).strip())
        else:
            # Fallback: search the entire page if customer section not found
            # Street address - pattern: "STR. VADENI 16"
            str_match = re.search(r"(STR\.[^\n]+)", page_text)
            if str_match:
                addr_lines.append(str_match.group(1).strip())
            
            # Postal code and city - pattern: "810176 BRAILA"
            postal_match = re.search(r"(\d{6}\s+[A-Z]+)", page_text)
            if postal_match:
                addr_lines.append(postal_match.group(1).strip())
            
            # Country - pattern: "ROMANIA"
            country_match = re.search(r"\n([A-Z]{2,}(?:\s+[A-Z]+)*)\s*\n", page_text)
            if country_match:
                addr_lines.append(country_match.group(1).strip())
        
        if addr_lines:
            bill_data.customer_address = format_address_lines(addr_lines)
    
    def _fix_data_mapping_issues(self, bill_data: BillData) -> None:
        """Fix common data mapping issues like currency/customer_code swap."""
        
        # Fix the currency/customer_code mapping issue observed in sample data
        if bill_data.currency is None and bill_data.customer_code == "EUR":
            bill_data.currency = "EUR"
            bill_data.customer_code = None
            logger.info("Fixed currency/customer_code mapping: moved EUR to currency field")
    
    def _extract_missing_from_filename(self, filename: str, bill_data: BillData) -> None:
        """Extract missing critical fields from filename as fallback."""
        
        if not filename:
            return
        
        # Extract total amount - pattern: "15473.37 €"
        if not bill_data.total_amount:
            total_amount = extract_numeric_from_filename(filename, r"([\d\.,]+)\s*€")
            if total_amount:
                bill_data.total_amount = str(total_amount)
        
        # Extract package count - pattern: "46 colli"
        if not bill_data.package_count:
            packages = extract_numeric_from_filename(filename, r"(\d+)\s*colli")
            if packages and isinstance(packages, int):
                bill_data.package_count = packages
        
        # Extract net weight - pattern: "(297.50 Kg_N"
        if not bill_data.net_weight_kg:
            net_weight = extract_numeric_from_filename(filename, r"\(([\d\.,]+)\s*Kg_N")
            if net_weight:
                bill_data.net_weight_kg = str(net_weight)
        
        # Extract gross weight - pattern: "328 Kg_B)"
        if not bill_data.gross_weight_kg:
            gross_weight = extract_numeric_from_filename(filename, r"([\d\.,]+)\s*Kg_B\)")
            if gross_weight:
                bill_data.gross_weight_kg = str(gross_weight)
        
        # Extract bill number from filename if not found in PDF
        if not bill_data.bill_number:
            bill_number = extract_numeric_from_filename(filename, r"nr\.\s*(\d+)")
            if bill_number:
                bill_data.bill_number = str(bill_number)
    
    def _extract_from_filename(self, filename: str, bill_data: BillData) -> BillData:
        """Complete fallback extraction from filename only."""
        
        if not filename:
            return bill_data
        
        logger.warning(f"Falling back to filename extraction for {filename}")
        
        # Extract all possible fields from filename
        self._extract_missing_from_filename(filename, bill_data)
        
        # Set default currency if not found
        if not bill_data.currency:
            if "€" in filename:
                bill_data.currency = "EUR"
        
        return bill_data