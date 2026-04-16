"""Graph execution engine — interprets Blockly workspace JSON and executes block handlers."""

from openfactcheck.engine import handlers
from openfactcheck.engine.block import Block
from openfactcheck.engine.errors import EngineError, UnknownBlockError
from openfactcheck.engine.executor import ExecutionResult, execute_pipeline

__all__ = [
    "Block",
    "EngineError",
    "ExecutionResult",
    "UnknownBlockError",
    "execute_pipeline",
    "handlers",
]
