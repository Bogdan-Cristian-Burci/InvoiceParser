from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime


@dataclass
class BillData:
    """Bill/Invoice general information"""
    bill_number: Optional[str] = None
    bill_date: Optional[str] = None
    currency: Optional[str] = None
    customer_code: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    customer_vat_id: Optional[str] = None
    gross_weight_kg: Optional[str] = None
    net_weight_kg: Optional[str] = None
    package_count: Optional[int] = None
    shipping_term: Optional[str] = None
    total_amount: Optional[str] = None


@dataclass
class DeliveryData:
    """Delivery note information"""
    ddt_series: Optional[str] = None
    ddt_number: Optional[str] = None
    ddt_date: Optional[str] = None
    ddt_reason: Optional[str] = None
    model_number: Optional[str] = None
    model_name: Optional[str] = None
    order_series: Optional[str] = None
    order_number: Optional[str] = None
    product_name: Optional[str] = None
    product_properties: Optional[str] = None
    products: List['ProductData'] = field(default_factory=list)


@dataclass
class ProductData:
    """Individual product line item"""
    product_code: Optional[str] = None
    description: Optional[str] = None
    customs_code: Optional[str] = None
    unit_of_measure: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    total_price: Optional[str] = None


@dataclass
class PageData:
    """Data extracted from a single page"""
    page_number: int
    raw_text: str
    tables: List[Any] = field(default_factory=list)
    products: List[ProductData] = field(default_factory=list)
    delivery_info: Optional[DeliveryData] = None
    all_deliveries: List[DeliveryData] = field(default_factory=list)  # NEW: Store all deliveries found on this page
    errors: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of OCR validation"""
    page_number: int
    is_valid: bool
    confidence_score: float
    validation_errors: List[str] = field(default_factory=list)
    corrected_data: Optional[Dict[str, Any]] = None


@dataclass
class ExtractionResult:
    """Complete extraction result"""
    success: bool
    bill_data: Optional[BillData] = None
    delivery_data: List[DeliveryData] = field(default_factory=list)  # Changed to List
    products: List[ProductData] = field(default_factory=list)
    page_data: List[PageData] = field(default_factory=list)
    validation_results: List[ValidationResult] = field(default_factory=list)
    extraction_method: str = "camelot+pdfminer"
    raw_text: Dict[str, str] = field(default_factory=dict)
    validation_checksum_ok: bool = False
    parsing_errors: List[str] = field(default_factory=list)
    message: str = ""


@dataclass
class ProcessingConfig:
    """Configuration for processing steps"""
    enable_ocr_validation: bool = True
    ocr_confidence_threshold: float = 0.8
    table_extraction_flavor: str = "lattice"
    line_scale: int = 30
    max_pages_to_process: Optional[int] = None
    validate_checksums: bool = True
    
    # LLMWhisperer configuration
    use_llmwhisperer: bool = False
    llmwhisperer_api_key: Optional[str] = None
    llmwhisperer_mode: str = "text"  # "text", "table", or "form"
    llmwhisperer_fallback: bool = True  # Fallback to other extractors if LLMWhisperer fails