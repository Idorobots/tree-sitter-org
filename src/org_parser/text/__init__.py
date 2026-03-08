"""Rich text and inline object representations.

This subpackage exposes :class:`RichText` together with public inline object
abstractions used to construct or inspect rich text programmatically.
"""

from org_parser.text._inline import (
    AngleLink,
    Bold,
    Citation,
    Code,
    CompletionCounter,
    ExportSnippet,
    FootnoteReference,
    InlineObject,
    InlineSourceBlock,
    Italic,
    LineBreak,
    PlainLink,
    PlainText,
    RadioTarget,
    RegularLink,
    StrikeThrough,
    Target,
    Timestamp,
    Underline,
    Verbatim,
)
from org_parser.text._rich_text import RichText

__all__ = [
    "AngleLink",
    "Bold",
    "Citation",
    "Code",
    "CompletionCounter",
    "ExportSnippet",
    "FootnoteReference",
    "InlineObject",
    "InlineSourceBlock",
    "Italic",
    "LineBreak",
    "PlainLink",
    "PlainText",
    "RadioTarget",
    "RegularLink",
    "RichText",
    "StrikeThrough",
    "Target",
    "Timestamp",
    "Underline",
    "Verbatim",
]
