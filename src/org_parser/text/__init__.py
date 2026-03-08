"""Rich text and markup object representations.

This subpackage provides Python types for Org Mode *objects* — the inline
content that can appear within element titles and body text, such as bold,
italic, and underline markup, links, timestamps, footnote references, and
export snippets.

The primary public type is :class:`RichText`, a stub that preserves verbatim
source text.  Richer inline-object decomposition will be added in subsequent
iterations.
"""

from org_parser.text._rich_text import RichText

__all__ = ["RichText"]
