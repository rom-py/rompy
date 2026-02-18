class UnsupportedOperation(Exception):
    """Raised when a transfer implementation doesn't support an operation."""

    def __init__(self, scheme: str, operation: str):
        self.scheme = scheme
        self.operation = operation
        super().__init__(f"Operation '{operation}' not supported for scheme '{scheme}'")
