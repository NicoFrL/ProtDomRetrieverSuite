from typing import Optional, Any, Dict
import requests
import logging

class ProcessingError(Exception):
    """Base exception for all processing errors"""
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class APIError(ProcessingError):
    """API-related errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[dict] = None):
        super().__init__(message, {'status_code': status_code, 'response': response})

class ValidationError(ProcessingError):
    """Data validation errors"""
    pass

class FileError(ProcessingError):
    """File operation errors"""
    pass

class NetworkError(ProcessingError):
    """Network-related errors"""
    pass

def handle_processing_errors(processor_method):
    """Decorator for handling processing errors"""
    def wrapper(self, *args, **kwargs):
        try:
            return processor_method(self, *args, **kwargs)
        except ProcessingError as e:
            self.logger.error(f"{type(e).__name__}: {e.message}")
            if e.details:
                self.logger.debug(f"Error details: {e.details}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise ProcessingError(f"Unexpected error during processing: {str(e)}")
    return wrapper

def validate_api_response(response: requests.Response,
                         context: str,
                         expected_status: int = 200) -> Dict[str, Any]:
    """
    Validate API response and return JSON data
    
    Args:
        response: Requests response object
        context: Context string for error message
        expected_status: Expected HTTP status code
        
    Returns:
        Response JSON data
        
    Raises:
        APIError: If response validation fails
    """
    if response.status_code != expected_status:
        raise APIError(
            f"API error during {context}",
            status_code=response.status_code,
            response=response.json() if response.headers.get('content-type', '').startswith('application/json') else None
        )
    
    try:
        return response.json()
    except ValueError:
        raise APIError(
            f"Invalid JSON response during {context}",
            status_code=response.status_code,
            response=response.text[:1000]  # Include first 1000 chars of response
        )

def validate_input_data(data: Any, name: str, required_fields: Optional[list] = None) -> None:
    """
    Validate input data
    
    Args:
        data: Data to validate
        name: Name of the data (for error messages)
        required_fields: Optional list of required field names
        
    Raises:
        ValidationError: If validation fails
    """
    if data is None:
        raise ValidationError(f"{name} is required")
        
    if required_fields:
        if not isinstance(data, dict):
            raise ValidationError(f"{name} must be a dictionary")
            
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(f"Missing required fields in {name}: {', '.join(missing_fields)}")
