"""Math block handlers — ``math_number``, ``math_arithmetic``, etc."""

import math
import random

from openfactcheck.engine import resolve
from openfactcheck.engine.block import Block
from openfactcheck.engine.context import ExecutionContext
from openfactcheck.engine.handler import handler


@handler("math_number")
def math_number(block: Block, ctx: ExecutionContext) -> float:
    """Return the numeric value from the NUM field."""
    return float(block.get_field("NUM", default="0"))


@handler("math_arithmetic")
def math_arithmetic(block: Block, ctx: ExecutionContext) -> float:
    """Binary arithmetic on A and B inputs."""
    op = block.get_field("OP", default="ADD")
    a = resolve.num(block, ctx, "A")
    b = resolve.num(block, ctx, "B")
    if op == "ADD":
        return a + b
    if op == "MINUS":
        return a - b
    if op == "MULTIPLY":
        return a * b
    if op == "DIVIDE":
        return a / b if b != 0 else float("inf")
    if op == "POWER":
        return a**b
    return 0.0


@handler("math_single")
def math_single(block: Block, ctx: ExecutionContext) -> float:
    """Unary math on the NUM input."""
    op = block.get_field("OP", default="ROOT")
    n = resolve.num(block, ctx, "NUM")
    if op == "ROOT":
        return math.sqrt(n)
    if op == "ABS":
        return abs(n)
    if op == "NEG":
        return -n
    if op == "LN":
        return math.log(n) if n > 0 else float("-inf")
    if op == "LOG10":
        return math.log10(n) if n > 0 else float("-inf")
    if op == "EXP":
        return math.exp(n)
    if op == "POW10":
        return 10**n
    return 0.0


@handler("math_trig")
def math_trig(block: Block, ctx: ExecutionContext) -> float:
    """Trigonometric functions. Blockly sends degrees; inverse returns degrees."""
    op = block.get_field("OP", default="SIN")
    n = resolve.num(block, ctx, "NUM")
    if op == "SIN":
        return math.sin(math.radians(n))
    if op == "COS":
        return math.cos(math.radians(n))
    if op == "TAN":
        return math.tan(math.radians(n))
    if op == "ASIN":
        return math.degrees(math.asin(n))
    if op == "ACOS":
        return math.degrees(math.acos(n))
    if op == "ATAN":
        return math.degrees(math.atan(n))
    return 0.0


MATH_CONSTANTS: dict[str, float] = {
    "PI": math.pi,
    "E": math.e,
    "GOLDEN_RATIO": (1 + math.sqrt(5)) / 2,
    "SQRT2": math.sqrt(2),
    "SQRT1_2": math.sqrt(0.5),
    "INFINITY": float("inf"),
}


@handler("math_constant")
def math_constant(block: Block, ctx: ExecutionContext) -> float:
    """Return a named math constant."""
    return MATH_CONSTANTS.get(block.get_field("CONSTANT", default="PI"), 0.0)


@handler("math_number_property")
def math_number_property(block: Block, ctx: ExecutionContext) -> bool:
    """Check a property of the number input."""
    prop = block.get_field("PROPERTY", default="EVEN")
    n = resolve.num(block, ctx, "NUMBER_TO_CHECK")
    if prop == "EVEN":
        return n % 2 == 0
    if prop == "ODD":
        return n % 2 == 1
    if prop == "PRIME":
        return _is_prime(int(n))
    if prop == "WHOLE":
        return n == int(n)
    if prop == "POSITIVE":
        return n > 0
    if prop == "NEGATIVE":
        return n < 0
    if prop == "DIVISIBLE_BY":
        d = resolve.num(block, ctx, "DIVISOR")
        return d != 0 and n % d == 0
    return False


@handler("math_round")
def math_round(block: Block, ctx: ExecutionContext) -> float:
    """Round, ceil, or floor the NUM input."""
    op = block.get_field("OP", default="ROUND")
    n = resolve.num(block, ctx, "NUM")
    if op == "ROUND":
        return round(n)
    if op == "ROUNDUP":
        return math.ceil(n)
    if op == "ROUNDDOWN":
        return math.floor(n)
    return n


@handler("math_modulo")
def math_modulo(block: Block, ctx: ExecutionContext) -> float:
    """Remainder of DIVIDEND / DIVISOR."""
    dividend = resolve.num(block, ctx, "DIVIDEND")
    divisor = resolve.num(block, ctx, "DIVISOR")
    return dividend % divisor if divisor != 0 else float("nan")


@handler("math_constrain")
def math_constrain(block: Block, ctx: ExecutionContext) -> float:
    """Clamp VALUE between LOW and HIGH."""
    return max(resolve.num(block, ctx, "LOW"), min(resolve.num(block, ctx, "VALUE"), resolve.num(block, ctx, "HIGH")))


@handler("math_random_int")
def math_random_int(block: Block, ctx: ExecutionContext) -> int:
    """Random integer between FROM and TO (inclusive)."""
    a = resolve.integer(block, ctx, "FROM")
    b = resolve.integer(block, ctx, "TO")
    return random.randint(min(a, b), max(a, b))


@handler("math_random_float")
def math_random_float(block: Block, ctx: ExecutionContext) -> float:
    """Random float in [0, 1)."""
    return random.random()


@handler("math_on_list")
def math_on_list(block: Block, ctx: ExecutionContext) -> float:
    """Aggregate operation on a list of numbers."""
    op = block.get_field("OP", default="SUM")
    raw = resolve.items(block, ctx, "LIST")
    nums = [float(x) for x in raw if x is not None]  # type: ignore[arg-type]
    if not nums:
        return 0.0
    if op == "SUM":
        return sum(nums)
    if op == "MIN":
        return min(nums)
    if op == "MAX":
        return max(nums)
    if op == "AVERAGE":
        return sum(nums) / len(nums)
    if op == "MEDIAN":
        return _median(nums)
    if op == "MODE":
        return _mode(nums)
    if op == "STD_DEV":
        return _std_dev(nums)
    if op == "RANDOM":
        return random.choice(nums)
    return 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def _median(nums: list[float]) -> float:
    s = sorted(nums)
    mid = len(s) // 2
    return (s[mid - 1] + s[mid]) / 2 if len(s) % 2 == 0 else s[mid]


def _mode(nums: list[float]) -> float:
    counts: dict[float, int] = {}
    for n in nums:
        counts[n] = counts.get(n, 0) + 1
    return max(counts, key=lambda k: counts[k])


def _std_dev(nums: list[float]) -> float:
    mean = sum(nums) / len(nums)
    variance = sum((x - mean) ** 2 for x in nums) / len(nums)
    return math.sqrt(variance)
