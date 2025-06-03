from flask import Flask, request, jsonify
import json
import os
import tempfile
import logging
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.invoice_processor import InvoiceProcessor
from src.utils.helpers import decimal_to_string_default
from src.utils.config import ConfigManager

# Initialize Flask app
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Set our app loggers to DEBUG for detailed extraction logging
logging.getLogger('src.extractors.table_extractor').setLevel(logging.DEBUG)
logging.getLogger('src.invoice_processor').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize invoice processor with configuration
config = ConfigManager.load_config()
invoice_processor = InvoiceProcessor(config)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy', 
        'service': 'invoice-pdf-parser', 
        'version': '2.0',
        'architecture': 'modular-step-based'
    })


@app.route('/config', methods=['GET'])
def get_config():
    """Get current configuration (for debugging)."""
    return jsonify({
        'ocr_validation_enabled': config.enable_ocr_validation,
        'ocr_confidence_threshold': config.ocr_confidence_threshold,
        'table_extraction_flavor': config.table_extraction_flavor,
        'line_scale': config.line_scale,
        'max_pages_to_process': config.max_pages_to_process,
        'validate_checksums': config.validate_checksums
    })


@app.route('/parse-invoice', methods=['POST'])
def parse_invoice_route():
    """
    Main invoice parsing endpoint.
    
    Processes uploaded PDF files through the step-based pipeline:
    1. Extract general metadata
    2. Process each page for table data
    3. Validate with OCR
    4. Compile final response
    """
    logger.info(f"Received request to /parse-invoice from {request.remote_addr}")
    
    try:
        # Validate request
        if 'file' not in request.files:
            logger.warning("No 'file' part in the request.")
            return jsonify({
                'success': False, 
                'error': 'No file uploaded',
                'message': 'Please ensure the POST request includes a file with key "file".'
            }), 400

        file = request.files['file']
        if not file or file.filename == '':
            logger.warning("No file selected for uploading.")
            return jsonify({
                'success': False, 
                'error': 'No file selected',
                'message': 'Please select a PDF file to upload.'
            }), 400

        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({
                'success': False, 
                'error': 'Invalid file type',
                'message': 'Only PDF files are supported. Received: ' + file.filename
            }), 400

        logger.info(f"Processing uploaded file: {file.filename}")

        # Process file using temporary storage
        with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp_file_obj:
            file.save(tmp_file_obj.name)
            
            logger.info(f"Parsing PDF at temporary path: {tmp_file_obj.name}")
            
            # Process through the new modular pipeline
            laravel_response = invoice_processor.process_invoice(tmp_file_obj.name)
            
            logger.info(f"Processing complete for {file.filename}. Success: {laravel_response.get('success', False)}")
            
            # Return JSON response with proper Decimal serialization
            return app.response_class(
                response=json.dumps(laravel_response, default=decimal_to_string_default),
                status=200,
                mimetype='application/json'
            )

    except Exception as e:
        logger.error(f"Unhandled error in /parse-invoice endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error: ' + str(e),
            'message': 'An unexpected error occurred during processing. Please check server logs.'
        }), 500


@app.route('/parse-invoice/stats', methods=['POST'])
def parse_invoice_stats():
    """
    Parse invoice and return processing statistics.
    Useful for monitoring and debugging.
    """
    logger.info(f"Received request to /parse-invoice/stats from {request.remote_addr}")
    
    try:
        # Same validation as main endpoint
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file or file.filename == '' or not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Invalid file'}), 400

        with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp_file_obj:
            file.save(tmp_file_obj.name)
            
            # Process and get stats
            laravel_response = invoice_processor.process_invoice(tmp_file_obj.name)
            
            # Create a mock ExtractionResult for stats (simplified)
            from src.models.invoice_models import ExtractionResult
            extraction_result = ExtractionResult(success=laravel_response['success'])
            extraction_result.parsing_errors = laravel_response['data'].get('parsing_errors', [])
            extraction_result.validation_checksum_ok = laravel_response['data'].get('validation_checksum_ok', False)
            
            stats = invoice_processor.get_processing_stats(extraction_result)
            
            return jsonify({
                'success': laravel_response['success'],
                'stats': stats,
                'message': laravel_response.get('message', '')
            })

    except Exception as e:
        logger.error(f"Error in /parse-invoice/stats endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # For local development. Use Gunicorn or similar in production.
    logger.info("Starting Invoice Parser Service v2.0 with modular architecture")
    app.run(host='0.0.0.0', port=5000, debug=True)