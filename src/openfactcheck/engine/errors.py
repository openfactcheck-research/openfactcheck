"""Engine error types."""


class EngineError(Exception):
    """Base exception for all engine execution failures.

    Caught by :func:`~openfactcheck.engine.executor.execute_pipeline` and
    converted to a failed :class:`~openfactcheck.engine.executor.ExecutionResult`.
    """


class UnknownBlockError(EngineError):
    """Raised when a block type has no registered handler.

    This typically means a block was added to the frontend toolbox
    but no corresponding handler function has been registered
    on the server.
    """

    def __init__(self, block_type: str) -> None:
        super().__init__(f"No handler for block type: {block_type}")
        self.block_type = block_type
