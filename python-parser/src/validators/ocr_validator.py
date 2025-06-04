import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from ..models.invoice_models import PageData, ValidationResult, ProductData, ProcessingConfig
from ..utils.helpers import parse_italian_decimal

logger = logging.getLogger(__name__)


class OCRValidator:
    """Validates extracted table data using OCR and cross-referencing."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
    
    def validate_page_data(self, page_data: PageData) -> ValidationResult:
        """
        Validate extracted data from a single page using OCR and consistency checks.
        Returns validation results with confidence scores and corrections.
        """
        validation_result = ValidationResult(
            page_number=page_data.page_number,
            is_valid=True,
            confidence_score=1.0
        )
        
        if not self.config.enable_ocr_validation:
            validation_result.confidence_score = 0.8  # Assume lower confidence without OCR
            return validation_result
        
        try:
            # Validate product data consistency
            product_validation = self._validate_products_consistency(page_data.products)
            validation_result.validation_errors.extend(product_validation['errors'])
            
            # Cross-reference with raw text
            text_validation = self._cross_reference_with_text(page_data.products, page_data.raw_text)
            validation_result.validation_errors.extend(text_validation['errors'])
            
            # Calculate overall confidence score
            validation_result.confidence_score = self._calculate_confidence_score(
                product_validation, text_validation
            )
            
            # Determine if validation passed
            validation_result.is_valid = (
                validation_result.confidence_score >= self.config.ocr_confidence_threshold
                and len(validation_result.validation_errors) == 0
            )
            
            # Generate corrected data if needed
            if not validation_result.is_valid:
                validation_result.corrected_data = self._generate_corrections(
                    page_data.products, validation_result.validation_errors
                )
            
        except Exception as e:
            error_msg = f"OCR validation failed for page {page_data.page_number + 1}: {str(e)}"
            validation_result.validation_errors.append(error_msg)
            validation_result.is_valid = False
            validation_result.confidence_score = 0.0
            logger.error(error_msg, exc_info=True)
        
        return validation_result
    
    def _validate_products_consistency(self, products: List[ProductData]) -> Dict[str, Any]:
        """Validate internal consistency of product data."""
        
        errors = []
        valid_products = 0
        total_products = len(products)
        
        for i, product in enumerate(products):
            # Validate numeric fields
            quantity_valid = self._validate_numeric_field(product.quantity, "quantity", i)
            unit_price_valid = self._validate_numeric_field(product.unit_price, "unit_price", i)
            total_price_valid = self._validate_numeric_field(product.total_price, "total_price", i)
            
            if not (quantity_valid and unit_price_valid and total_price_valid):
                errors.append(f"Product {i + 1}: Invalid numeric fields")
                continue
            
            # Validate calculation: quantity * unit_price ≈ total_price
            if product.quantity and product.unit_price and product.total_price:
                calc_error = self._validate_price_calculation(product, i)
                if calc_error:
                    errors.append(calc_error)
                else:
                    valid_products += 1
            else:
                # Missing critical fields
                errors.append(f"Product {i + 1}: Missing critical pricing fields")
        
        consistency_score = valid_products / total_products if total_products > 0 else 0
        
        return {
            'errors': errors,
            'consistency_score': consistency_score,
            'valid_products': valid_products,
            'total_products': total_products
        }
    
    def _validate_numeric_field(self, field_value: Optional[str], field_name: str, product_index: int) -> bool:
        """Validate that a numeric field can be parsed correctly."""
        
        if not field_value:
            return False
        
        try:
            parsed = parse_italian_decimal(field_value)
            return parsed is not None and parsed >= 0
        except Exception:
            return False
    
    def _validate_price_calculation(self, product: ProductData, product_index: int) -> Optional[str]:
        """Validate that quantity * unit_price ≈ total_price."""
        
        try:
            quantity = parse_italian_decimal(product.quantity)
            unit_price = parse_italian_decimal(product.unit_price)
            total_price = parse_italian_decimal(product.total_price)
            
            if not all([quantity, unit_price, total_price]):
                return f"Product {product_index + 1}: Cannot parse pricing fields for calculation"
            
            calculated_total = quantity * unit_price
            difference = abs(calculated_total - total_price)
            tolerance = max(Decimal('0.01'), total_price * Decimal('0.001'))  # 0.1% tolerance or 1 cent minimum
            
            if difference > tolerance:
                return (f"Product {product_index + 1}: Price calculation mismatch. "
                       f"Expected: {calculated_total}, Found: {total_price}, Difference: {difference}")
            
            return None
            
        except Exception as e:
            return f"Product {product_index + 1}: Error validating price calculation: {str(e)}"
    
    def _cross_reference_with_text(self, products: List[ProductData], raw_text: str) -> Dict[str, Any]:
        """Cross-reference extracted product data with raw text."""
        
        errors = []
        found_products = 0
        
        if not raw_text:
            errors.append("No raw text available for cross-referencing")
            return {'errors': errors, 'text_match_score': 0.0}
        
        # Check if product codes appear in raw text
        for i, product in enumerate(products):
            if product.product_code:
                # Look for exact product code match
                if product.product_code in raw_text:
                    found_products += 1
                else:
                    # Try partial matches for codes with special characters
                    code_variants = self._generate_code_variants(product.product_code)
                    if any(variant in raw_text for variant in code_variants):
                        found_products += 1
                    else:
                        errors.append(f"Product {i + 1}: Code '{product.product_code}' not found in raw text")
        
        text_match_score = found_products / len(products) if products else 0
        
        return {
            'errors': errors,
            'text_match_score': text_match_score,
            'found_products': found_products
        }
    
    def _generate_code_variants(self, product_code: str) -> List[str]:
        """Generate possible variants of a product code for fuzzy matching."""
        
        variants = [product_code]
        
        # Remove special characters
        cleaned = ''.join(c for c in product_code if c.isalnum())
        if cleaned != product_code:
            variants.append(cleaned)
        
        # Replace dots with spaces and vice versa
        if '.' in product_code:
            variants.append(product_code.replace('.', ' '))
        if ' ' in product_code:
            variants.append(product_code.replace(' ', '.'))
        
        return list(set(variants))  # Remove duplicates
    
    def _calculate_confidence_score(self, product_validation: Dict[str, Any], text_validation: Dict[str, Any]) -> float:
        """Calculate overall confidence score based on validation results."""
        
        # Weight different validation aspects
        consistency_weight = 0.6
        text_match_weight = 0.4
        
        consistency_score = product_validation.get('consistency_score', 0.0)
        text_match_score = text_validation.get('text_match_score', 0.0)
        
        overall_score = (consistency_score * consistency_weight) + (text_match_score * text_match_weight)
        
        # Penalize for validation errors
        error_count = len(product_validation.get('errors', [])) + len(text_validation.get('errors', []))
        if error_count > 0:
            error_penalty = min(0.2 * error_count, 0.5)  # Max 50% penalty
            overall_score = max(0.0, overall_score - error_penalty)
        
        return round(overall_score, 3)
    
    def _generate_corrections(self, products: List[ProductData], errors: List[str]) -> Dict[str, Any]:
        """Generate potential corrections for validation errors."""
        
        corrections = {
            'corrected_products': [],
            'correction_notes': []
        }
        
        for i, product in enumerate(products):
            corrected_product = self._attempt_product_correction(product, i, errors)
            corrections['corrected_products'].append(corrected_product)
        
        # Add general correction notes
        if any("price calculation mismatch" in error.lower() for error in errors):
            corrections['correction_notes'].append(
                "Price calculation mismatches detected. Consider manual review of unit prices and totals."
            )
        
        if any("not found in raw text" in error.lower() for error in errors):
            corrections['correction_notes'].append(
                "Some product codes not found in raw text. OCR quality may be poor on this page."
            )
        
        return corrections
    
    def _attempt_product_correction(self, product: ProductData, index: int, errors: List[str]) -> ProductData:
        """Attempt to correct a single product's data."""
        
        # Create a copy of the product for correction
        corrected = ProductData()
        corrected.product_code = product.product_code
        corrected.description = product.description
        corrected.customs_code = product.customs_code
        # Note: material and width_cm attributes don't exist in current ProductData model
        corrected.unit_of_measure = product.unit_of_measure
        
        # Copy original values
        corrected.quantity = product.quantity
        corrected.unit_price = product.unit_price
        corrected.total_price = product.total_price
        
        # Attempt to fix price calculation if needed
        relevant_errors = [e for e in errors if f"Product {index + 1}" in e and "calculation mismatch" in e]
        if relevant_errors and product.quantity and product.unit_price:
            try:
                quantity = parse_italian_decimal(product.quantity)
                unit_price = parse_italian_decimal(product.unit_price)
                if quantity and unit_price:
                    corrected_total = quantity * unit_price
                    corrected.total_price = str(corrected_total)
            except Exception:
                pass  # Keep original value if correction fails
        
        return corrected