import os
import logging
from typing import Optional
from ..models.invoice_models import ProcessingConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration for the invoice processing pipeline."""
    
    @staticmethod
    def load_config() -> ProcessingConfig:
        """Load configuration from environment variables with sensible defaults."""
        
        config = ProcessingConfig()
        
        # OCR Validation settings
        config.enable_ocr_validation = ConfigManager._get_bool_env("ENABLE_OCR_VALIDATION", True)
        config.ocr_confidence_threshold = ConfigManager._get_float_env("OCR_CONFIDENCE_THRESHOLD", 0.8)
        
        # Table extraction settings
        config.table_extraction_flavor = ConfigManager._get_str_env("TABLE_EXTRACTION_FLAVOR", "lattice")
        config.line_scale = ConfigManager._get_int_env("LINE_SCALE", 30)
        
        # Processing limits
        config.max_pages_to_process = ConfigManager._get_optional_int_env("MAX_PAGES_TO_PROCESS", None)
        
        # Validation settings
        config.validate_checksums = ConfigManager._get_bool_env("VALIDATE_CHECKSUMS", True)
        
        logger.info(f"Loaded configuration: OCR={config.enable_ocr_validation}, "
                   f"Flavor={config.table_extraction_flavor}, "
                   f"LineScale={config.line_scale}")
        
        return config
    
    @staticmethod
    def _get_str_env(key: str, default: str) -> str:
        """Get string environment variable with default."""
        return os.environ.get(key, default)
    
    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """Get integer environment variable with default."""
        try:
            return int(os.environ.get(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    @staticmethod
    def _get_float_env(key: str, default: float) -> float:
        """Get float environment variable with default."""
        try:
            return float(os.environ.get(key, str(default)))
        except ValueError:
            logger.warning(f"Invalid float value for {key}, using default: {default}")
            return default
    
    @staticmethod
    def _get_bool_env(key: str, default: bool) -> bool:
        """Get boolean environment variable with default."""
        value = os.environ.get(key, "").lower()
        if value in ("true", "1", "yes", "on"):
            return True
        elif value in ("false", "0", "no", "off"):
            return False
        else:
            return default
    
    @staticmethod
    def _get_optional_int_env(key: str, default: Optional[int]) -> Optional[int]:
        """Get optional integer environment variable."""
        value = os.environ.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default