"""Utility functions."""  # hook test edit

x = 1
y = 2
z = 3


def greet():
    """Return greeting from OpenFactCheck."""
    x = 1
    y = 2
    z = 3
    return "Hello from OpenFactCheck v2"


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def ugly_function(a, b, c, d):
    if a == True and b != False:
        result = a + b + c
        return result
    else:
        return None
