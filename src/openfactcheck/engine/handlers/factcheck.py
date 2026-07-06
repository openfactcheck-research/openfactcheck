"""Handler for the Fact-Checking blocks: the OpenFactCheck pipeline runner.

The block names a prebuilt pipeline and, optionally, a language model; the handler
runs that pipeline over the ``input_text`` an Input Text block set, and prints the
resulting report. Provider and search API keys are read from the environment,
which the runner populates from the user's stored secrets.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, cast

from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.errors import EngineError
from openfactcheck.engine.handler import handler

if TYPE_CHECKING:
    from openfactcheck.components.types import Result
    from openfactcheck.config import ModelSpec


@handler("openfactcheck")
def openfactcheck(block: Block, ctx: ExecutionContext) -> object:
    """Run the block's prebuilt pipeline over ``input_text`` and print the result.

    The pipeline name comes from the block; a connected language model supplies its
    name and sampling parameters so the pipeline builds its own clients. The run
    happens in a worker thread because the facade drives its async graph with
    ``asyncio.run``, which cannot run inside the engine's event loop.
    """
    from openfactcheck import OpenFactCheck, OpenFactCheckConfig  # noqa: PLC0415 - lazy so engine startup stays light.

    input_text = ctx.variables.get("input_text")
    if not isinstance(input_text, str) or not input_text.strip():
        raise EngineError("OpenFactCheck needs an Input Text block above it.")

    pipeline = block.get_field("PIPELINE", default="factool")
    try:
        config = OpenFactCheckConfig(pipeline=pipeline, model=_model_spec(block))
        checker = OpenFactCheck(config)
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = cast("Result", pool.submit(checker.run, input_text).result())
    except Exception as e:
        raise EngineError(f"Fact-check failed: {e}") from e

    ctx.print(result.model_dump_json(indent=2))
    return result


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
