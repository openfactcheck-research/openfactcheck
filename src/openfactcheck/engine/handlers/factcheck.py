"""Handler for the Fact-Checking blocks: the OpenFactCheck pipeline runner.

The block names a prebuilt pipeline and, optionally, a language model; the handler
runs that pipeline over the ``input_text`` an Input Text block set, and prints the
resulting report. Provider and search API keys are read from the environment,
which the runner populates from the user's stored secrets.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, cast

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.errors import EngineError
from openfactcheck.engine.events import NodeEmittedEvent, NodeFailedEvent, NodeFinishedEvent, NodeStartedEvent
from openfactcheck.engine.handler import handler

if TYPE_CHECKING:
    from openfactcheck._core import OpenFactCheck
    from openfactcheck.components.types import Result
    from openfactcheck.config import ModelSpec

# Node roles (the segment after the namespace in a node id) whose progress the frontend renders.
_CLAIM_PROCESSOR_ROLE = "claim_processor"
_VERIFIER_ROLE = "verifier"


@handler("openfactcheck")
def openfactcheck(block: Block, ctx: ExecutionContext) -> object:
    """Run the block's prebuilt pipeline over ``input_text`` and print the result.

    The pipeline name comes from the block; a connected language model supplies its
    name and sampling parameters so the pipeline builds its own clients. When the run
    is streamed, each pipeline step is forwarded to the engine as it starts and
    finishes; otherwise the pipeline runs to completion in a worker thread (the facade
    drives its async graph with ``asyncio.run``, which cannot run inside the engine's
    event loop).
    """
    from openfactcheck import OpenFactCheck, OpenFactCheckConfig  # noqa: PLC0415 - lazy so engine startup stays light.

    input_text = ctx.variables.get("input_text")
    if not isinstance(input_text, str) or not input_text.strip():
        raise EngineError("OpenFactCheck needs an Input Text block above it.")

    pipeline = block.get_field("PIPELINE", default="factool")
    try:
        config = OpenFactCheckConfig(pipeline=pipeline, model=_model_spec(block))
        checker = OpenFactCheck(config)
        result = _stream_run(checker, input_text, ctx) if ctx.streaming else _blocking_run(checker, input_text)
    except Exception as e:
        raise EngineError(f"Fact-check failed: {e}") from e

    ctx.print(result.model_dump_json(indent=2))
    return result


def _blocking_run(checker: "OpenFactCheck", input_text: str) -> "Result":
    """Run the pipeline to completion in a worker thread, since the facade drives ``asyncio.run``."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        return cast("Result", pool.submit(checker.run, input_text).result())


def _stream_run(checker: "OpenFactCheck", input_text: str, ctx: ExecutionContext) -> "Result":
    """Drive the pipeline's event stream, forwarding each step (and per-claim reasoning and verdicts)."""
    from openfactcheck.graph import NodeEmitted, NodeFailed, NodeFinished, NodeStarted, RunFinished  # noqa: PLC0415

    async def drive() -> object:
        final: object = None
        async for event in checker.astream(input_text):
            match event:
                case NodeStarted(node_id=node_id, fork_stack=fork_stack):
                    ctx.emit(NodeStartedEvent(node_id=node_id, branch=_branch(fork_stack)))
                case NodeFinished(node_id=node_id, output=output, duration=duration, fork_stack=fork_stack):
                    ctx.emit(
                        NodeFinishedEvent(
                            node_id=node_id,
                            duration=duration,
                            branch=_branch(fork_stack),
                            output=_finished_payload(node_id, output),
                        )
                    )
                case NodeFailed(node_id=node_id, error=error, fork_stack=fork_stack):
                    ctx.emit(NodeFailedEvent(node_id=node_id, error=str(error), branch=_branch(fork_stack)))
                case NodeEmitted(node_id=node_id, data=data, fork_stack=fork_stack):
                    if (payload := _emitted_payload(node_id, data)) is not None:
                        ctx.emit(NodeEmittedEvent(node_id=node_id, branch=_branch(fork_stack), data=payload))
                case RunFinished(output=output):
                    final = output

        return final

    return cast("Result", asyncio.run(drive()))


def _branch(fork_stack: tuple[Any, ...]) -> int | None:
    """The innermost fan-out branch index of a task (for example a claim index), or None at the graph root."""
    return fork_stack[-1].branch_index if fork_stack else None


def _finished_payload(node_id: str, output: object) -> object | None:
    """Curate a step's output: claim texts from the claim processor, a trimmed verdict from the verifier."""
    from openfactcheck.components.types import Claim, Verdict  # noqa: PLC0415 - lazy so engine startup stays light.

    role = node_id.rsplit("/", 1)[-1]
    if role == _CLAIM_PROCESSOR_ROLE and isinstance(output, list):
        return [claim.text for claim in output if isinstance(claim, Claim)]
    if role == _VERIFIER_ROLE and isinstance(output, Verdict):
        return {
            "label": output.label,
            "reasoning": output.reasoning,
            "correction": output.correction,
            "error": output.error,
        }
    return None


def _emitted_payload(node_id: str, data: object) -> object | None:
    """Curate a step's live emission: the verifier's partial reasoning; nothing else is surfaced."""
    if node_id.rsplit("/", 1)[-1] != _VERIFIER_ROLE:
        return None
    reasoning = getattr(data, "reasoning", None)
    return {"reasoning": reasoning} if isinstance(reasoning, str) and reasoning else None


def _model_spec(block: Block) -> "ModelSpec | None":
    """Read the connected language model into a spec, or ``None`` for the pipeline default."""
    from openfactcheck import ModelSpec  # noqa: PLC0415 - lazy so engine startup stays light.

    model_block = block.get_input_block("MODEL")
    if model_block is None:
        return None
    name = model_block.get_extra("model")
    if not isinstance(name, str) or not name:
        return None

    provider = model_block.get_field("PROVIDER", default="openai")
    spec: dict[str, object] = {
        "name": f"{provider}/{name}",
        "temperature": model_block.get_extra("temperature"),
        "top_p": model_block.get_extra("topP"),
        "max_output_tokens": model_block.get_extra("maxTokens"),
    }
    # Penalties and reasoning effort apply to OpenAI-compatible providers only.
    if provider in ("openai", "openrouter"):
        spec["frequency_penalty"] = model_block.get_extra("freqPenalty")
        spec["presence_penalty"] = model_block.get_extra("presPenalty")
        spec["reasoning_effort"] = model_block.get_extra("reasoningEffort")

    return ModelSpec.model_validate({key: value for key, value in spec.items() if value is not None})
