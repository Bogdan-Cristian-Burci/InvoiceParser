import re
import logging
from decimal import Decimal, InvalidOperation
from typing import Optional, Union

logger = logging.getLogger(__name__)


def parse_italian_decimal(text_value: Union[str, int, float, Decimal, None]) -> Optional[Decimal]:
    """Converts Italian-style numbers (e.g., '1.234,56') to Decimal. Returns None if invalid."""
    if text_value is None:
        return None
    if isinstance(text_value, Decimal):
        return text_value
    if isinstance(text_value, (int, float)):
        return Decimal(str(text_value))
    if not isinstance(text_value, str):
        logger.warning(f"parse_italian_decimal received non-string/non-numeric type: {type(text_value)}")
        return None

    cleaned_value = text_value.strip()
    if not cleaned_value:
        return None

    # Debug logging for problematic values
    if "126" in cleaned_value or "1269" in cleaned_value:
        logger.debug(f"Parsing potential problematic value: '{cleaned_value}'")

    try:
        # Enhanced Italian decimal parsing
        # Handle different cases:
        # 1. "126,911" -> "126.911" (decimal comma)
        # 2. "1.234,56" -> "1234.56" (thousands separator + decimal comma)
        # 3. "1234.56" -> "1234.56" (already correct format)
        # 4. "1234" -> "1234" (integer)
        
        if ',' in cleaned_value and '.' in cleaned_value:
            # Both comma and dot present: dot is thousands separator, comma is decimal
            # Example: "1.234,56" -> "1234.56"
            parts = cleaned_value.split(',')
            if len(parts) == 2:
                integer_part = parts[0].replace('.', '')
                decimal_part = parts[1]
                standardized_value = f"{integer_part}.{decimal_part}"
            else:
                standardized_value = cleaned_value.replace('.', '').replace(',', '.')
        elif ',' in cleaned_value:
            # Only comma present: it's the decimal separator
            # Example: "126,911" -> "126.911"
            standardized_value = cleaned_value.replace(',', '.')
        else:
            # Only dots or no separators: assume it's already in correct format
            standardized_value = cleaned_value
            
        result = Decimal(standardized_value)
        
        # Debug logging for problematic values
        if "126" in cleaned_value or "1269" in cleaned_value:
            logger.debug(f"Parsed '{cleaned_value}' -> '{standardized_value}' -> {result}")
            
        return result
        
    except InvalidOperation:
        # Fallback: if there's extra text, try to extract just the numeric part
        match = re.search(r'([-+]?\d*[.,]?\d+)', cleaned_value)
        if match:
            try:
                fallback_value = match.group(1).replace(',', '.')
                result = Decimal(fallback_value)
                logger.debug(f"Fallback parsed '{cleaned_value}' -> '{fallback_value}' -> {result}")
                return result
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


def clean_string_field(value: str) -> Optional[str]:
    """Clean and validate string fields, return None for empty or 'nan' values."""
    if not value or not isinstance(value, str):
        return None
    
    cleaned = value.strip()
    if not cleaned or cleaned.lower() == 'nan':
        return None
    
    return cleaned


def extract_numeric_from_filename(filename: str, pattern: str) -> Optional[Union[Decimal, int]]:
    """Extract numeric values from filename using regex pattern."""
    if not filename:
        return None
    
    match = re.search(pattern, filename)
    if match:
        try:
            value = match.group(1)
            if '.' in value or ',' in value:
                return parse_italian_decimal(value)
            else:
                return int(value)
        except (ValueError, InvalidOperation):
            logger.warning(f"Could not parse numeric value from filename pattern: {pattern}")
    
    return None


def validate_customer_data_mapping(parsed_data: dict) -> dict:
    """Fix common data mapping issues like currency/customer_code swap."""
    # Fix currency/customer_code mapping issue
    if parsed_data.get("currency") is None and parsed_data.get("customer_code") == "EUR":
        parsed_data["currency"] = "EUR"
        parsed_data["customer_code"] = None
    
    # Try to extract customer code from other fields if missing
    if not parsed_data.get("customer_code") and parsed_data.get("customer_name"):
        # Look for patterns like MSCE00068 in the raw text
        # This would need access to raw text, so we'll implement this in the extractor
        pass
    
    return parsed_data


def format_address_lines(addr_parts: list) -> Optional[str]:
    """Format address components into a single address string."""
    if not addr_parts:
        return None
    
    # Filter out empty strings and 'nan' values
    clean_parts = [part.strip() for part in addr_parts if part and str(part).strip().lower() != 'nan']
    
    if not clean_parts:
        return None
    
    return ", ".join(clean_parts)