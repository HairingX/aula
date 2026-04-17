class ParseError(Exception):
    """
    Exception raised when parsing the response from the server fails.
    """

class AulaCredentialError(Exception):
    """
    Exception raised when the credentials were rejected.
    """

class AulaApiError(Exception):
    """
    Exception raised for non-credential API errors (e.g., unexpected HTTP status codes).
    Unlike AulaCredentialError, this does NOT trigger MitID re-authentication.
    """
