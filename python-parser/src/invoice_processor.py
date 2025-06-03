import logging
from typing import Dict, Any
from .models.invoice_models import ExtractionResult, ProcessingConfig
from .extractors.metadata_extractor import MetadataExtractor
from .extractors.table_extractor import TableExtractor
from .extractors.response_compiler import ResponseCompiler
from .validators.ocr_validator import OCRValidator
from .utils.pdf_utils import split_pdf_into_pages, validate_pdf_file
from .utils.config import ConfigManager

logger = logging.getLogger(__name__)


class InvoiceProcessor:
    """Main orchestrator for the step-by-step invoice processing pipeline."""
    
    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ConfigManager.load_config()
        
        # Initialize processing components
        self.metadata_extractor = MetadataExtractor()
        self.table_extractor = TableExtractor(self.config)
        self.ocr_validator = OCRValidator(self.config)
        self.response_compiler = ResponseCompiler(self.config)
    
    def process_invoice(self, pdf_path: str) -> Dict[str, Any]:
        """
        Main entry point for processing an invoice PDF.
        Returns a Laravel-compatible response dictionary.
        """
        logger.info(f"Starting invoice processing for: {pdf_path}")
        
        try:
            # Step 0: Validate PDF file
            if not validate_pdf_file(pdf_path):
                return self._create_error_response("Invalid or unreadable PDF file")
            
            # Step 1: Extract general metadata
            logger.info("Step 1: Extracting general metadata...")
            bill_data = self.metadata_extractor.extract_general_metadata(pdf_path)
            
            # Step 2: Split PDF into pages and process each page
            logger.info("Step 2: Processing pages...")
            page_numbers = split_pdf_into_pages(pdf_path)
            if not page_numbers:
                return self._create_error_response("Could not determine PDF page structure")
            
            # Apply max pages limit if configured
            if self.config.max_pages_to_process:
                page_numbers = page_numbers[:self.config.max_pages_to_process]
                logger.info(f"Limited processing to {len(page_numbers)} pages")
            
            page_data_list = []
            for page_num in page_numbers:
                logger.info(f"Processing page {page_num + 1}...")
                page_data = self.table_extractor.extract_page_data(pdf_path, page_num)
                page_data_list.append(page_data)
            
            # Step 3: OCR validation for each page
            logger.info("Step 3: Validating extracted data...")
            validation_results = []
            for page_data in page_data_list:
                validation_result = self.ocr_validator.validate_page_data(page_data)
                validation_results.append(validation_result)
                
                if not validation_result.is_valid:
                    logger.warning(f"Page {page_data.page_number + 1} failed validation with confidence: {validation_result.confidence_score}")
            
            # Step 4: Compile final response
            logger.info("Step 4: Compiling final response...")
            extraction_result = self.response_compiler.compile_final_result(
                bill_data, page_data_list, validation_results, pdf_path
            )
            
            # Convert to Laravel format
            laravel_response = self.response_compiler.convert_to_laravel_format(extraction_result)
            
            logger.info(f"Invoice processing completed. Success: {extraction_result.success}")
            return laravel_response
            
        except Exception as e:
            error_msg = f"Unhandled error during invoice processing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._create_error_response(error_msg)
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {
            "success": False,
            "data": {
                "bill": {},
                "delivery": {},
                "products": [],
                "extraction_method": "failed",
                "raw_text": {},
                "validation_checksum_ok": False,
                "parsing_errors": [error_message]
            },
            "message": "Invoice processing failed"
        }
    
    def get_processing_stats(self, extraction_result: ExtractionResult) -> Dict[str, Any]:
        """Get processing statistics for monitoring and debugging."""
        
        stats = {
            "total_pages_processed": len(extraction_result.page_data),
            "total_products_extracted": len(extraction_result.products),
            "pages_with_errors": sum(1 for p in extraction_result.page_data if p.errors),
            "validation_failures": sum(1 for v in extraction_result.validation_results if not v.is_valid),
            "average_confidence": 0.0,
            "checksum_valid": extraction_result.validation_checksum_ok,
            "total_parsing_errors": len(extraction_result.parsing_errors)
        }
        
        # Calculate average confidence
        if extraction_result.validation_results:
            total_confidence = sum(v.confidence_score for v in extraction_result.validation_results)
            stats["average_confidence"] = total_confidence / len(extraction_result.validation_results)
        
        return stats