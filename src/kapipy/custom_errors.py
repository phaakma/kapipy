"""
custom_errors.py
Custom exceptions.
"""

class HTTPError(Exception):
    """Base exception for HTTP errors."""

class BadRequest(HTTPError):
    """Exception raised for HTTP 400 Bad Request errors."""

class Unauthorized(HTTPError):
    """Exception raised for HTTP 401 Unauthorized errors."""

class NotFound(HTTPError):
    """Exception raised for HTTP 404 Not Found errors."""

class ServerError(HTTPError):
    """Exception raised for HTTP 500 Server Error errors."""

class ExportError(Exception):
    """Custom exception for errors encountered during export operations."""

class UnknownItemTypeError(Exception):
    """
    Exception raised when an unknown item type is encountered.

    This exception is used to signal that an item kind is not supported by the client.

    Parameters:
        message (str): Description of the error.

    Attributes:
        message (str): Description of the error.
    """
    def __init__(self, message: str):
        """
        Initializes the UnknownItemTypeError with a descriptive error message.

        Parameters:
            message (str): Description of the error.
        """
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the error.

        Returns:
            str: The error message.
        """
        return self.message