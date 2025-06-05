import logging
import os
from typing import Dict, Any, Optional
from llmwhisperer_client.client import LLMWhispererClient
from llmwhisperer_client.client import LLMWhispererClientException

logger = logging.getLogger(__name__)


class LLMWhispererExtractor:
    """
    LLMWhisperer extractor for PDF text extraction.
    Integrates with the existing modular pipeline.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize LLMWhisperer client.
        
        Args:
            api_key: LLMWhisperer API key. If None, will try to get from environment.
        """
        self.api_key = api_key or os.getenv('LLMWHISPERER_API_KEY')
        if not self.api_key:
            raise ValueError("LLMWhisperer API key is required. Set LLMWHISPERER_API_KEY environment variable or pass api_key parameter.")
        
        self.client = LLMWhispererClient(api_key=self.api_key)
        logger.info("LLMWhisperer client initialized")
    
    def extract_text(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """
        Extract text from PDF using LLMWhisperer.
        
        Args:
            pdf_path: Path to the PDF file
            **kwargs: Additional parameters for LLMWhisperer (e.g., mode, pages_to_extract, etc.)
        
        Returns:
            Dict containing extracted text and metadata
        """
        try:
            logger.info(f"Extracting text from {pdf_path} using LLMWhisperer")
            
            # Default parameters
            extraction_params = {
                'mode': 'text',  # 'text', 'form', or 'table'
                'output_mode': 'text',
                'url_or_file_path': pdf_path,
                **kwargs  # Allow override of default parameters
            }
            
            # Call LLMWhisperer API
            result = self.client.whisper(**extraction_params)
            
            logger.info(f"LLMWhisperer extraction completed for {pdf_path}")
            
            return {
                'success': True,
                'extracted_text': result['extracted_text'],
                'status_code': result.get('status_code'),
                'whisper_hash': result.get('whisper-hash'),
                'metadata': {
                    'extraction_mode': extraction_params['mode'],
                    'output_mode': extraction_params['output_mode'],
                    'file_path': pdf_path
                }
            }
            
        except LLMWhispererClientException as e:
            logger.error(f"LLMWhisperer API error: {e}")
            return {
                'success': False,
                'error': f"LLMWhisperer API error: {str(e)}",
                'extracted_text': None,
                'metadata': {'file_path': pdf_path}
            }
        except Exception as e:
            logger.error(f"Unexpected error during LLMWhisperer extraction: {e}")
            return {
                'success': False,
                'error': f"Extraction error: {str(e)}",
                'extracted_text': None,
                'metadata': {'file_path': pdf_path}
            }
    
    def extract_table_mode(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """
        Extract text optimized for table data using LLMWhisperer table mode.
        
        Args:
            pdf_path: Path to the PDF file
            **kwargs: Additional parameters for LLMWhisperer
        
        Returns:
            Dict containing extracted text and metadata
        """
        table_params = {
            'mode': 'table',
            'output_mode': 'text',
            **kwargs
        }
        
        return self.extract_text(pdf_path, **table_params)
    
    def extract_form_mode(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """
        Extract text optimized for form data using LLMWhisperer form mode.
        
        Args:
            pdf_path: Path to the PDF file
            **kwargs: Additional parameters for LLMWhisperer
        
        Returns:
            Dict containing extracted text and metadata
        """
        form_params = {
            'mode': 'form',
            'output_mode': 'text',
            **kwargs
        }
        
        return self.extract_text(pdf_path, **form_params)
    
    def extract_specific_pages(self, pdf_path: str, pages: list, mode: str = 'text', **kwargs) -> Dict[str, Any]:
        """
        Extract text from specific pages using LLMWhisperer.
        
        Args:
            pdf_path: Path to the PDF file
            pages: List of page numbers to extract (1-indexed)
            mode: Extraction mode ('text', 'table', or 'form')
            **kwargs: Additional parameters for LLMWhisperer
        
        Returns:
            Dict containing extracted text and metadata
        """
        page_params = {
            'mode': mode,
            'pages_to_extract': ','.join(map(str, pages)),
            **kwargs
        }
        
        return self.extract_text(pdf_path, **page_params)