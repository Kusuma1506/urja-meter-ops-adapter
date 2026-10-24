class UrjaAdapterError(Exception):
    """Base application error."""


class ConfigurationError(UrjaAdapterError):
    """Raised when required settings are absent or invalid."""


class UpstreamError(UrjaAdapterError):
    """Raised when the legacy portal returns a failure response."""

    def __init__(self, message: str, code: str = "UPSTREAM_ERROR", status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class UpstreamAuthenticationError(UpstreamError):
    def __init__(self, message: str = "Upstream authentication failed."):
        super().__init__(message, code="UPSTREAM_AUTH_FAILED", status_code=401)


class UpstreamTimeoutError(UpstreamError):
    def __init__(self, message: str = "The legacy portal did not respond in time."):
        super().__init__(message, code="UPSTREAM_TIMEOUT", status_code=504)


class UpstreamBadResponseError(UpstreamError):
    def __init__(self, message: str = "The legacy portal returned an unexpected response."):
        super().__init__(message, code="UPSTREAM_BAD_RESPONSE", status_code=502)


class MeterNotFoundError(UrjaAdapterError):
    def __init__(self, meter_id: str):
        super().__init__(f"Meter {meter_id} was not found.")
        self.meter_id = meter_id
        self.code = "METER_NOT_FOUND"
        self.status_code = 404


class ValidationError(UrjaAdapterError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
        self.code = "VALIDATION_ERROR"
        self.status_code = 400
