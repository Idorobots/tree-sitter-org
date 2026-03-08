"""Time-related semantic objects for Org content.

This subpackage currently exposes :class:`Timestamp` and will host additional
time abstractions in future iterations.
"""

from org_parser.time._timestamp import Timestamp

__all__ = ["Timestamp"]
