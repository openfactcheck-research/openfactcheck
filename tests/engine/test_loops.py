"""Tests for loop block handlers."""

from typing import Any

import pytest

from openfactcheck.engine import execute_pipeline

pytestmark = pytest.mark.asyncio(loop_scope="function")


def _pipeline(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"blocks": {"blocks": list(blocks)}}


def _num(value: float) -> dict[str, Any]:
    return {"type": "math_number", "id": "n1", "fields": {"NUM": str(value)}}


def _bool(value: bool) -> dict[str, Any]:
    return {"type": "logic_boolean", "id": "b1", "fields": {"BOOL": "TRUE" if value else "FALSE"}}


def _print_text(text: str, *, block_id: str = "p1") -> dict[str, Any]:
    return {
        "type": "text_print",
        "id": block_id,
        "inputs": {"TEXT": {"block": {"type": "text", "id": f"{block_id}_t", "fields": {"TEXT": text}}}},
    }


def _print_var(var_name: str, *, block_id: str = "pv1") -> dict[str, Any]:
    return {
        "type": "text_print",
        "id": block_id,
        "inputs": {"TEXT": {"block": {"type": "variables_get", "id": f"{block_id}_v", "fields": {"VAR": var_name}}}},
    }


def _break() -> dict[str, Any]:
    return {"type": "controls_flow_statements", "id": "brk1", "fields": {"FLOW": "BREAK"}}


def _continue(next_block: dict[str, Any] | None = None) -> dict[str, Any]:
    block: dict[str, Any] = {"type": "controls_flow_statements", "id": "cnt1", "fields": {"FLOW": "CONTINUE"}}
    if next_block:
        block["next"] = {"block": next_block}
    return block


# ---------------------------------------------------------------------------
# controls_repeat_ext
# ---------------------------------------------------------------------------


async def test_repeat_basic() -> None:
    block = {
        "type": "controls_repeat_ext",
        "id": "rep1",
        "inputs": {
            "TIMES": {"block": _num(3)},
            "DO": {"block": _print_text("hi")},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "hi\nhi\nhi"


async def test_repeat_zero() -> None:
    block = {
        "type": "controls_repeat_ext",
        "id": "rep1",
        "inputs": {
            "TIMES": {"block": _num(0)},
            "DO": {"block": _print_text("nope")},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == ""


async def test_repeat_with_break() -> None:
    body = _print_text("a")
    body["next"] = {"block": _break()}
    block = {
        "type": "controls_repeat_ext",
        "id": "rep1",
        "inputs": {
            "TIMES": {"block": _num(5)},
            "DO": {"block": body},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "a"


# ---------------------------------------------------------------------------
# controls_whileUntil
# ---------------------------------------------------------------------------


async def test_while_loop() -> None:
    """While loop: print i, increment, stop when i > 2."""
    # Set i = 0 → while i < 3: print i, i = i + 1
    set_i = {
        "type": "variables_set",
        "id": "vs1",
        "fields": {"VAR": "i"},
        "inputs": {"VALUE": {"block": _num(0)}},
        "next": {
            "block": {
                "type": "controls_whileUntil",
                "id": "wh1",
                "fields": {"MODE": "WHILE"},
                "inputs": {
                    "BOOL": {
                        "block": {
                            "type": "logic_compare",
                            "id": "cmp1",
                            "fields": {"OP": "LT"},
                            "inputs": {
                                "A": {"block": {"type": "variables_get", "id": "vg1", "fields": {"VAR": "i"}}},
                                "B": {"block": _num(3)},
                            },
                        }
                    },
                    "DO": {
                        "block": {
                            "type": "text_print",
                            "id": "p1",
                            "inputs": {
                                "TEXT": {
                                    "block": {"type": "variables_get", "id": "vg2", "fields": {"VAR": "i"}}
                                }
                            },
                            "next": {
                                "block": {
                                    "type": "variables_set",
                                    "id": "vs2",
                                    "fields": {"VAR": "i"},
                                    "inputs": {
                                        "VALUE": {
                                            "block": {
                                                "type": "math_arithmetic",
                                                "id": "add1",
                                                "fields": {"OP": "ADD"},
                                                "inputs": {
                                                    "A": {
                                                        "block": {
                                                            "type": "variables_get",
                                                            "id": "vg3",
                                                            "fields": {"VAR": "i"},
                                                        }
                                                    },
                                                    "B": {"block": _num(1)},
                                                },
                                            }
                                        }
                                    },
                                }
                            },
                        }
                    },
                },
            }
        },
    }
    result = await execute_pipeline(_pipeline(set_i))
    assert result.output == "0.0\n1.0\n2.0"


async def test_until_loop() -> None:
    """Until loop: repeat until condition is true."""
    set_i = {
        "type": "variables_set",
        "id": "vs1",
        "fields": {"VAR": "i"},
        "inputs": {"VALUE": {"block": _num(0)}},
        "next": {
            "block": {
                "type": "controls_whileUntil",
                "id": "wh1",
                "fields": {"MODE": "UNTIL"},
                "inputs": {
                    "BOOL": {
                        "block": {
                            "type": "logic_compare",
                            "id": "cmp1",
                            "fields": {"OP": "EQ"},
                            "inputs": {
                                "A": {"block": {"type": "variables_get", "id": "vg1", "fields": {"VAR": "i"}}},
                                "B": {"block": _num(3)},
                            },
                        }
                    },
                    "DO": {
                        "block": {
                            "type": "text_print",
                            "id": "p1",
                            "inputs": {
                                "TEXT": {
                                    "block": {"type": "variables_get", "id": "vg2", "fields": {"VAR": "i"}}
                                }
                            },
                            "next": {
                                "block": {
                                    "type": "variables_set",
                                    "id": "vs2",
                                    "fields": {"VAR": "i"},
                                    "inputs": {
                                        "VALUE": {
                                            "block": {
                                                "type": "math_arithmetic",
                                                "id": "add1",
                                                "fields": {"OP": "ADD"},
                                                "inputs": {
                                                    "A": {
                                                        "block": {
                                                            "type": "variables_get",
                                                            "id": "vg3",
                                                            "fields": {"VAR": "i"},
                                                        }
                                                    },
                                                    "B": {"block": _num(1)},
                                                },
                                            }
                                        }
                                    },
                                }
                            },
                        }
                    },
                },
            }
        },
    }
    result = await execute_pipeline(_pipeline(set_i))
    assert result.output == "0.0\n1.0\n2.0"


# ---------------------------------------------------------------------------
# controls_for
# ---------------------------------------------------------------------------


async def test_for_loop() -> None:
    block = {
        "type": "controls_for",
        "id": "for1",
        "fields": {"VAR": "i"},
        "inputs": {
            "FROM": {"block": _num(1)},
            "TO": {"block": _num(5)},
            "BY": {"block": _num(1)},
            "DO": {"block": _print_var("i")},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "1.0\n2.0\n3.0\n4.0\n5.0"


async def test_for_loop_step_2() -> None:
    block = {
        "type": "controls_for",
        "id": "for1",
        "fields": {"VAR": "i"},
        "inputs": {
            "FROM": {"block": _num(0)},
            "TO": {"block": _num(10)},
            "BY": {"block": _num(3)},
            "DO": {"block": _print_var("i")},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "0.0\n3.0\n6.0\n9.0"


async def test_for_loop_countdown() -> None:
    block = {
        "type": "controls_for",
        "id": "for1",
        "fields": {"VAR": "i"},
        "inputs": {
            "FROM": {"block": _num(3)},
            "TO": {"block": _num(1)},
            "BY": {"block": _num(-1)},
            "DO": {"block": _print_var("i")},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "3.0\n2.0\n1.0"


async def test_for_loop_with_break() -> None:
    body = _print_var("i")
    # Break when i == 3
    body["next"] = {
        "block": {
            "type": "controls_if",
            "id": "if1",
            "inputs": {
                "IF0": {
                    "block": {
                        "type": "logic_compare",
                        "id": "cmp1",
                        "fields": {"OP": "EQ"},
                        "inputs": {
                            "A": {"block": {"type": "variables_get", "id": "vg2", "fields": {"VAR": "i"}}},
                            "B": {"block": _num(3)},
                        },
                    }
                },
                "DO0": {"block": _break()},
            },
        }
    }
    block = {
        "type": "controls_for",
        "id": "for1",
        "fields": {"VAR": "i"},
        "inputs": {
            "FROM": {"block": _num(1)},
            "TO": {"block": _num(10)},
            "BY": {"block": _num(1)},
            "DO": {"block": body},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "1.0\n2.0\n3.0"


# ---------------------------------------------------------------------------
# controls_forEach
# ---------------------------------------------------------------------------


async def test_for_each() -> None:
    list_block = {
        "type": "lists_create_with",
        "id": "list1",
        "inputs": {
            "ADD0": {"block": {"type": "text", "id": "t1", "fields": {"TEXT": "a"}}},
            "ADD1": {"block": {"type": "text", "id": "t2", "fields": {"TEXT": "b"}}},
            "ADD2": {"block": {"type": "text", "id": "t3", "fields": {"TEXT": "c"}}},
        },
    }
    block = {
        "type": "controls_forEach",
        "id": "fe1",
        "fields": {"VAR": "item"},
        "inputs": {
            "LIST": {"block": list_block},
            "DO": {"block": _print_var("item")},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    assert result.output == "a\nb\nc"


# ---------------------------------------------------------------------------
# controls_flow_statements (continue)
# ---------------------------------------------------------------------------


async def test_continue_skips_rest() -> None:
    """Continue skips printing 'after' but loop continues."""
    body = _print_var("i")
    body["next"] = {"block": _continue(next_block=_print_text("after", block_id="p2"))}
    block = {
        "type": "controls_for",
        "id": "for1",
        "fields": {"VAR": "i"},
        "inputs": {
            "FROM": {"block": _num(1)},
            "TO": {"block": _num(3)},
            "BY": {"block": _num(1)},
            "DO": {"block": body},
        },
    }
    result = await execute_pipeline(_pipeline(block))
    # "after" never prints because continue skips it
    assert result.output == "1.0\n2.0\n3.0"
