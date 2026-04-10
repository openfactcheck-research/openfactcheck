"""Graph execution engine — interprets Blockly workspace JSON and executes block handlers."""

import openfactcheck.engine.handlers as handlers  # noqa: F401 — auto-registers all block handlers
from openfactcheck.engine.block import Block
from openfactcheck.engine.context import EngineError, UnknownBlockError
from openfactcheck.engine.executor import ExecutionResult, execute_pipeline

__all__ = ["Block", "EngineError", "ExecutionResult", "UnknownBlockError", "execute_pipeline", "handlers"]
