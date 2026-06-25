"""Error hierarchy for the configuration layer.

Every configuration failure derives from [`ConfigError`][ConfigError]: a model
name whose provider rejects one of its sampling parameters, a malformed run
configuration, and so on. Catch it to handle any configuration problem in one
place.
"""


class ConfigError(Exception):
    """Base exception for every configuration error.

    Raised when a configuration value cannot be resolved into a valid run, for
    example a model name whose provider does not accept one of its sampling
    parameters. The message names what was wrong; the underlying cause, when
    there is one, is chained.
    """
