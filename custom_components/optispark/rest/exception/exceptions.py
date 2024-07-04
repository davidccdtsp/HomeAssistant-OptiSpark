
__all__ = [
    "OptisparkApiClientError",
    "OptisparkApiClientTimeoutError",
    "OptisparkApiClientCommunicationError",
    "OptisparkApiClientAuthenticationError",
    "OptisparkApiClientLambdaError",
    "OptisparkApiClientPostcodeError",
    "OptisparkApiClientUnitError"
]
class OptisparkApiClientError(Exception):
    """Exception to indicate a general API error."""


class OptisparkApiClientTimeoutError(OptisparkApiClientError):
    """Lamba probably took too long starting up."""


class OptisparkApiClientCommunicationError(OptisparkApiClientError):
    """Exception to indicate a communication error."""


class OptisparkApiClientAuthenticationError(OptisparkApiClientError):
    """Exception to indicate an authentication error."""


class OptisparkApiClientLambdaError(OptisparkApiClientError):
    """Exception to indicate lambda return an error."""


class OptisparkApiClientPostcodeError(OptisparkApiClientError):
    """Exception to indicate invalid postcode."""


class OptisparkApiClientUnitError(OptisparkApiClientError):
    """Exception to indicate unit error."""
