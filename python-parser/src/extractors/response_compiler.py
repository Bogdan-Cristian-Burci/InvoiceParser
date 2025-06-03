import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from ..models.invoice_models import (
    ExtractionResult, BillData, DeliveryData, ProductData, 
    PageData, ValidationResult, ProcessingConfig
)
from ..utils.helpers import parse_italian_decimal

logger = logging.getLogger(__name__)


class ResponseCompiler:
    """Compiles final response from all extraction and validation results."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
    
    def compile_final_result(
        self,
        bill_data: BillData,
        page_data_list: List[PageData],
        validation_results: List[ValidationResult],
        pdf_filename: str
    ) -> ExtractionResult:
        """
        Compile the final extraction result from all processing steps.
        """
        result = ExtractionResult(success=True)
        result.bill_data = bill_data
        
        try:
            # Compile delivery data (use first delivery info found)
            result.delivery_data = self._compile_delivery_data(page_data_list)
            
            # Compile all products from all pages
            result.products = self._compile_products(page_data_list, validation_results)
            
            # Store page data and validation results
            result.page_data = page_data_list
            result.validation_results = validation_results
            
            # Compile raw text summary
            result.raw_text = self._compile_raw_text(page_data_list)
            
            # Perform final validations and checksums
            self._perform_final_validations(result)
            
            # Extract footer information (weights, totals, etc.)
            self._extract_footer_information(result, page_data_list)
            
            # Set success status and message
            result.success = len(result.parsing_errors) == 0
            result.message = self._generate_final_message(result)
            
        except Exception as e:
            error_msg = f"Error compiling final result: {str(e)}"
            result.parsing_errors.append(error_msg)
            result.success = False
            result.message = "Compilation failed with errors"
            logger.error(error_msg, exc_info=True)
        
        return result
    
    def _compile_delivery_data(self, page_data_list: List[PageData]) -> List[DeliveryData]:
        """Compile all delivery data found across pages using the new all_deliveries approach."""
        
        deliveries = []
        
        # NEW APPROACH: Collect ALL deliveries from all pages
        for page_data in page_data_list:
            # Use the new all_deliveries field if available, otherwise fall back to single delivery_info
            page_deliveries = getattr(page_data, 'all_deliveries', [])
            if not page_deliveries and page_data.delivery_info:
                # Fallback for backward compatibility
                page_deliveries = [page_data.delivery_info]
                # For backward compatibility, if using single delivery_info, associate all page products
                if page_data.delivery_info:
                    page_data.delivery_info.products = page_data.products
            
            # Add all deliveries found on this page
            for delivery in page_deliveries:
                # Products should already be associated via _associate_products_with_deliveries in table_extractor
                # If not (e.g., no products on this page), ensure products list exists
                if not hasattr(delivery, 'products') or delivery.products is None:
                    delivery.products = []
                
                deliveries.append(delivery)
                logger.debug(f"Found delivery {delivery.ddt_series} {delivery.ddt_number} with {len(delivery.products)} associated products")
        
        if not deliveries:
            # If no delivery data found, create a minimal one with all products
            logger.warning("No delivery data found in any page")
            all_products = []
            for page_data in page_data_list:
                all_products.extend(page_data.products)
            
            minimal_delivery = DeliveryData()
            minimal_delivery.products = all_products
            deliveries.append(minimal_delivery)
        
        # FIX: Handle cross-page delivery data merging
        deliveries = self._merge_cross_page_deliveries(deliveries, page_data_list)
        
        # Remove duplicates based on DDT series and number, merging their products
        unique_deliveries = []
        seen_ddts = {}
        for delivery in deliveries:
            ddt_key = f"{delivery.ddt_series}_{delivery.ddt_number}"
            if ddt_key not in seen_ddts:
                seen_ddts[ddt_key] = delivery
                unique_deliveries.append(delivery)
            else:
                # Merge products from duplicate delivery
                existing_delivery = seen_ddts[ddt_key]
                existing_delivery.products.extend(delivery.products)
                logger.debug(f"Merged duplicate delivery {delivery.ddt_series} {delivery.ddt_number}, now has {len(existing_delivery.products)} products")
        
        logger.info(f"Compiled {len(unique_deliveries)} unique deliveries total (from {len(deliveries)} found)")
        return unique_deliveries
    
    def _merge_cross_page_deliveries(self, deliveries: List[DeliveryData], page_data_list: List[PageData]) -> List[DeliveryData]:
        """
        Handle cross-page delivery data by merging incomplete delivery records and
        extracting missing product details from subsequent pages.
        """
        import re
        
        # Find deliveries with incomplete data (missing model_number or product details)
        incomplete_deliveries = []
        complete_deliveries = []
        
        for delivery in deliveries:
            # A delivery is incomplete if it has DDT info but missing model_number or product details
            if (delivery.ddt_series and delivery.ddt_number and 
                (not delivery.model_number or not delivery.product_name)):
                incomplete_deliveries.append(delivery)
                logger.debug(f"Found incomplete delivery: {delivery.ddt_series} {delivery.ddt_number} (missing: {'model_number' if not delivery.model_number else ''} {'product_name' if not delivery.product_name else ''})")
            else:
                complete_deliveries.append(delivery)
        
        # For each incomplete delivery, search subsequent pages for missing data
        for incomplete_delivery in incomplete_deliveries:
            logger.debug(f"Attempting to complete delivery: {incomplete_delivery.ddt_series} {incomplete_delivery.ddt_number}")
            
            # Find the page where this incomplete delivery was found
            source_page = None
            for page_data in page_data_list:
                if incomplete_delivery in getattr(page_data, 'all_deliveries', [page_data.delivery_info] if page_data.delivery_info else []):
                    source_page = page_data.page_number
                    break
            
            if source_page is None:
                logger.warning(f"Could not find source page for incomplete delivery: {incomplete_delivery.ddt_series} {incomplete_delivery.ddt_number}")
                complete_deliveries.append(incomplete_delivery)  # Add as-is
                continue
            
            # Search next few pages for the missing product details
            found_completion = False
            for page_data in page_data_list:
                if page_data.page_number <= source_page:
                    continue  # Only look at subsequent pages
                
                if page_data.page_number > source_page + 2:
                    break  # Don't look too far ahead
                
                # Search this page's raw text for product details that match our incomplete delivery
                completion_data = self._extract_delivery_completion(incomplete_delivery, page_data.raw_text)
                if completion_data:
                    # Merge the completion data into the incomplete delivery
                    if completion_data.get('model_number'):
                        incomplete_delivery.model_number = completion_data['model_number']
                    if completion_data.get('model_name'):
                        incomplete_delivery.model_name = completion_data['model_name']
                    if completion_data.get('order_series'):
                        incomplete_delivery.order_series = completion_data['order_series']
                    if completion_data.get('order_number'):
                        incomplete_delivery.order_number = completion_data['order_number']
                    if completion_data.get('product_name'):
                        incomplete_delivery.product_name = completion_data['product_name']
                    if completion_data.get('product_properties'):
                        incomplete_delivery.product_properties = completion_data['product_properties']
                    
                    logger.info(f"Successfully completed delivery {incomplete_delivery.ddt_series} {incomplete_delivery.ddt_number} with data from page {page_data.page_number + 1}")
                    found_completion = True
                    break
            
            if not found_completion:
                logger.warning(f"Could not find completion data for delivery: {incomplete_delivery.ddt_series} {incomplete_delivery.ddt_number}")
            
            complete_deliveries.append(incomplete_delivery)
        
        return complete_deliveries
    
    def _extract_delivery_completion(self, incomplete_delivery: DeliveryData, page_text: str) -> Optional[Dict[str, str]]:
        """
        Extract missing delivery data from a page's raw text.
        Looks for product details that appear early in the page (likely continuation from previous page).
        """
        import re
        
        if not page_text:
            return None
        
        # Look for product details in the first part of the page (first 1000 characters)
        # This is where cross-page continuation data would appear
        search_text = page_text[:1000]
        
        completion_data = {}
        
        # Extract model_number, order_series, and order_number from line like "MMM25.291160436.70 / MS5CE0002 1225"
        model_order_patterns = [
            r"([A-Z0-9.]+)\s*/\s*([A-Z0-9]{9})\s+(\d+)",  # With / separator
            r"([A-Z0-9.]+)\s+([A-Z0-9]{9})\s+(\d+)",      # Without / separator
            r"([A-Z0-9.]+)\s*/\s*([A-Z0-9]+)\s+(\d+)"     # With / and flexible order series length
        ]
        
        for pattern in model_order_patterns:
            model_order_match = re.search(pattern, search_text)
            if model_order_match:
                completion_data['model_number'] = model_order_match.group(1).strip()
                completion_data['order_series'] = model_order_match.group(2).strip()
                completion_data['order_number'] = model_order_match.group(3).strip()
                logger.debug(f"Found model/order completion: {completion_data['model_number']}, {completion_data['order_series']}, {completion_data['order_number']}")
                break
        
        # Extract product_properties from line like "Tessuto: 100% Cotone"
        properties_match = re.search(r"Tessuto:\s*([^\n]+)", search_text)
        if properties_match:
            completion_data['product_properties'] = properties_match.group(1).strip()
            logger.debug(f"Found properties completion: {completion_data['product_properties']}")
        
        # Extract product_name and model_name
        # Look for pattern: properties line, then product_name line, then model_name line
        product_name_match = re.search(r"Tessuto:[^\n]+\n\s*([A-Z]+)\n\s*([A-Z]+)", search_text)
        if product_name_match:
            completion_data['product_name'] = product_name_match.group(1).strip()
            completion_data['model_name'] = product_name_match.group(2).strip()
            logger.debug(f"Found product/model name completion: {completion_data['product_name']}, {completion_data['model_name']}")
        
        # Only return completion data if we found at least one field
        if completion_data:
            return completion_data
        
        return None
    
    def _compile_products(self, page_data_list: List[PageData], validation_results: List[ValidationResult]) -> List[ProductData]:
        """Compile all products from all pages, applying corrections if available."""
        
        all_products = []
        
        for i, page_data in enumerate(page_data_list):
            # Get validation result for this page
            validation_result = None
            if i < len(validation_results):
                validation_result = validation_results[i]
            
            # Use corrected products if available and validation failed
            if (validation_result and 
                not validation_result.is_valid and 
                validation_result.corrected_data and 
                'corrected_products' in validation_result.corrected_data):
                
                corrected_products = validation_result.corrected_data['corrected_products']
                all_products.extend(corrected_products)
                logger.info(f"Used corrected products for page {page_data.page_number + 1}")
            else:
                # Use original products
                all_products.extend(page_data.products)
        
        return all_products
    
    def _compile_raw_text(self, page_data_list: List[PageData]) -> Dict[str, str]:
        """Compile raw text from all pages."""
        
        raw_text = {}
        for page_data in page_data_list:
            page_key = f"page{page_data.page_number + 1}"
            # Limit text length for storage
            raw_text[page_key] = page_data.raw_text[:5000] if page_data.raw_text else ""
        
        return raw_text
    
    def _perform_final_validations(self, result: ExtractionResult) -> None:
        """Perform final validations including checksum validation."""
        
        if not self.config.validate_checksums:
            return
        
        try:
            # Calculate total from all products
            calculated_total = Decimal('0.0')
            for product in result.products:
                if product.total_price:
                    product_total = parse_italian_decimal(product.total_price)
                    if product_total:
                        calculated_total += product_total
            
            # Compare with stated total
            if result.bill_data and result.bill_data.total_amount:
                stated_total = parse_italian_decimal(result.bill_data.total_amount)
                if stated_total:
                    difference = abs(stated_total - calculated_total)
                    tolerance = Decimal('0.01')  # 1 cent tolerance
                    
                    if difference <= tolerance:
                        result.validation_checksum_ok = True
                    else:
                        error_msg = (f"Checksum Mismatch: Stated Grand Total {stated_total}, "
                                   f"Calculated Sum {calculated_total}, Difference: {difference}")
                        result.parsing_errors.append(error_msg)
                        logger.warning(error_msg)
                else:
                    result.parsing_errors.append("Could not parse stated total amount for checksum validation")
            else:
                result.parsing_errors.append("No total amount found for checksum validation")
                
        except Exception as e:
            error_msg = f"Error during checksum validation: {str(e)}"
            result.parsing_errors.append(error_msg)
            logger.error(error_msg)
    
    def _extract_footer_information(self, result: ExtractionResult, page_data_list: List[PageData]) -> None:
        """Extract footer information from the last few pages."""
        
        if not page_data_list:
            return
        
        # Search last 2 pages for footer information
        pages_to_search = page_data_list[-2:] if len(page_data_list) >= 2 else page_data_list
        
        for page_data in reversed(pages_to_search):  # Start from the last page
            if not page_data.raw_text:
                continue
            
            footer_text = page_data.raw_text
            
            # Extract total amount if not already found
            if not result.bill_data.total_amount:
                total_patterns = [
                    r"Tot\s*importo:\s*\(\s*EUR\s*\)\s*([\d\.,]+)",
                    r"Tot(?:ale)?\s*importo:\s*\(\s*EUR\s*\)\s*([\d\.,]+)",
                    r"Tot(?:ale)?\s*importo:\s*([\d\.,]+)",
                    r"Totale:\s*([\d\.,]+)",
                    r"TOTALE:\s*([\d\.,]+)"
                ]
                
                for pattern in total_patterns:
                    import re
                    match = re.search(pattern, footer_text, re.IGNORECASE)
                    if match:
                        total_amount = parse_italian_decimal(match.group(1))
                        if total_amount:
                            result.bill_data.total_amount = str(total_amount)
                            break
            
            # Extract shipping terms
            if not result.bill_data.shipping_term:
                import re
                match = re.search(r"Porto:\s*(.*)", footer_text)
                if match:
                    result.bill_data.shipping_term = match.group(1).strip()
            
            # Extract package count
            if not result.bill_data.package_count:
                package_patterns = [
                    r"Numero colli:\s*(\d+)",
                    r"N\.\s*colli:\s*(\d+)",
                    r"Colli:\s*(\d+)"
                ]
                
                for pattern in package_patterns:
                    import re
                    match = re.search(pattern, footer_text, re.IGNORECASE)
                    if match:
                        try:
                            result.bill_data.package_count = int(match.group(1))
                            break
                        except ValueError:
                            pass
            
            # Extract weights
            if not result.bill_data.net_weight_kg:
                net_patterns = [
                    r"Peso netto \( KG \):\s*([\d\.,]+)",
                    r"Peso\s*netto\s*\(\s*KG\s*\):\s*([\d\.,]+)",
                    r"Peso\s*netto:\s*([\d\.,]+)"
                ]
                
                for pattern in net_patterns:
                    import re
                    match = re.search(pattern, footer_text, re.IGNORECASE)
                    if match:
                        net_weight = parse_italian_decimal(match.group(1))
                        if net_weight:
                            result.bill_data.net_weight_kg = str(net_weight)
                            break
            
            if not result.bill_data.gross_weight_kg:
                gross_patterns = [
                    r"Peso lordo \( KG \):\s*([\d\.,]+)",
                    r"Peso\s*lordo\s*\(\s*KG\s*\):\s*([\d\.,]+)",
                    r"Peso\s*lordo:\s*([\d\.,]+)"
                ]
                
                for pattern in gross_patterns:
                    import re
                    match = re.search(pattern, footer_text, re.IGNORECASE)
                    if match:
                        gross_weight = parse_italian_decimal(match.group(1))
                        if gross_weight:
                            result.bill_data.gross_weight_kg = str(gross_weight)
                            break
    
    def _generate_final_message(self, result: ExtractionResult) -> str:
        """Generate final status message based on extraction results."""
        
        if not result.success:
            return "Invoice parsing failed with errors. Check parsing_errors field for details."
        
        if result.parsing_errors:
            return "Invoice parsing completed with warnings. Check parsing_errors field for details."
        
        if not result.validation_checksum_ok:
            return "Invoice parsing completed but checksum validation failed."
        
        # Check validation results
        failed_validations = [v for v in result.validation_results if not v.is_valid]
        if failed_validations:
            return f"Invoice parsing completed but {len(failed_validations)} pages failed OCR validation."
        
        return "Invoice parsing completed successfully."
    
    def convert_to_laravel_format(self, extraction_result: ExtractionResult) -> Dict[str, Any]:
        """Convert ExtractionResult to Laravel-compatible format."""
        
        # Convert BillData to dict
        bill_dict = self._convert_bill_data(extraction_result.bill_data)
        
        # Convert DeliveryData list to dict list
        deliveries_list = [self._convert_delivery_data(d) for d in extraction_result.delivery_data]
        
        # Convert ProductData list to dict list
        products_list = [self._convert_product_data(p) for p in extraction_result.products]
        
        return {
            "success": extraction_result.success,
            "data": {
                "bill": bill_dict,
                "deliveries": deliveries_list,
                "extraction_method": extraction_result.extraction_method,
                "raw_text": extraction_result.raw_text,
                "validation_checksum_ok": extraction_result.validation_checksum_ok,
                "parsing_errors": extraction_result.parsing_errors
            },
            "message": extraction_result.message
        }
    
    def _convert_bill_data(self, bill_data: Optional[BillData]) -> Dict[str, Any]:
        """Convert BillData to dictionary."""
        if not bill_data:
            return {}
        
        return {
            "bill_number": bill_data.bill_number,
            "bill_date": bill_data.bill_date,
            "currency": bill_data.currency,
            "customer_code": bill_data.customer_code,
            "customer_name": bill_data.customer_name,
            "customer_address": bill_data.customer_address,
            "gross_weight_kg": bill_data.gross_weight_kg,
            "net_weight_kg": bill_data.net_weight_kg,
            "package_count": bill_data.package_count,
            "shipping_term": bill_data.shipping_term,
            "total_amount": bill_data.total_amount
        }
    
    def _convert_delivery_data(self, delivery_data: Optional[DeliveryData]) -> Dict[str, Any]:
        """Convert DeliveryData to dictionary including associated products."""
        if not delivery_data:
            return {}
        
        # Convert associated products to dictionary format
        products_list = []
        if hasattr(delivery_data, 'products') and delivery_data.products:
            products_list = [self._convert_product_data(p) for p in delivery_data.products]
        
        return {
            "ddt_series": delivery_data.ddt_series,
            "ddt_number": delivery_data.ddt_number,
            "ddt_date": delivery_data.ddt_date,
            "ddt_reason": delivery_data.ddt_reason,
            "model_number": delivery_data.model_number,
            "model_name": delivery_data.model_name,
            "order_series": delivery_data.order_series,
            "order_number": delivery_data.order_number,
            "product_name": delivery_data.product_name,
            "product_properties": delivery_data.product_properties,
            "products": products_list
        }
    
    def _convert_product_data(self, product_data: ProductData) -> Dict[str, Any]:
        """Convert ProductData to dictionary."""
        return {
            "product_code": product_data.product_code,
            "description": product_data.description,
            "unit_of_measure": product_data.unit_of_measure,
            "quantity": product_data.quantity,
            "unit_price": product_data.unit_price,
            "total_price": product_data.total_price
        }