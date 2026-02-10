import logging

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self._available = False
        self._error = "OCR module not implemented or missing dependencies."

    def is_available(self) -> bool:
        return self._available

    def get_error(self) -> str:
        return self._error

    def parse_cnic_data(self, front_path: str, back_path: str) -> dict:
        """
        Parses CNIC data from front and back images.
        Returns a dictionary with extracted fields.
        """
        logger.warning("OCR service called but is unavailable.")
        raise NotImplementedError("OCR service is not available.")

ocr_service = OCRService()
