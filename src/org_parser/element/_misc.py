"""Semantic element classes for miscellaneous structural Org nodes.

This module covers the smaller structural node types that appear as direct
children of section bodies but do not belong to any other element module:

* :class:`BlankLine` — an empty separator line (``blank_line`` node).
* :class:`CaptionKeyword` — a ``#+CAPTION:`` affiliated keyword line.
* :class:`Comment` — a single-line ``#`` comment.
* :class:`HorizontalRule` — a ``-----`` horizontal rule line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from org_parser._node import node_source, node_text
from org_parser.element._element import Element, build_semantic_repr

if TYPE_CHECKING:
    import tree_sitter

    from org_parser.document._document import Document
    from org_parser.document._heading import Heading

__all__ = [
    "BlankLine",
    "CaptionKeyword",
    "Comment",
    "HorizontalRule",
]


class BlankLine(Element):
    """A blank separator line between body elements.

    Org Mode blank lines are structurally significant — they separate
    elements — but carry no semantic content of their own.
    """

    @classmethod
    def from_node(
        cls,
        node: tree_sitter.Node,
        document: Document | None = None,
        *,
        parent: Document | Heading | Element | None = None,
    ) -> BlankLine:
        """Create a :class:`BlankLine` from a ``blank_line`` node."""
        elem = cls(parent=parent)
        elem.attach_backing(node, document)
        return elem

    def __str__(self) -> str:
        """Render the blank line, preserving source while parse-backed and clean."""
        if not self.dirty and self._node is not None and self._document is not None:
            return node_source(self._node, self._document)
        return "\n"

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return "BlankLine()"


class Comment(Element):
    """A single-line ``#`` comment.

    Args:
        text: The comment body text, excluding the leading ``#`` marker and
            optional following space.
    """

    def __init__(
        self,
        *,
        text: str,
        parent: Document | Heading | Element | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._text = text

    @classmethod
    def from_node(
        cls,
        node: tree_sitter.Node,
        document: Document | None = None,
        *,
        parent: Document | Heading | Element | None = None,
    ) -> Comment:
        """Create a :class:`Comment` from a ``comment`` node."""
        raw = node_source(node, document).rstrip("\n")
        if raw.startswith("# "):
            text = raw[2:]
        elif raw.startswith("#"):
            text = raw[1:]
        else:
            text = raw
        elem = cls(text=text, parent=parent)
        elem.attach_backing(node, document)
        return elem

    @property
    def text(self) -> str:
        """Mutable comment body text (excluding the ``#`` prefix)."""
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        """Set comment body text and mark this element as dirty."""
        self._text = value
        self._mark_dirty()

    def __str__(self) -> str:
        """Render the comment line, preserving source while parse-backed and clean."""
        if not self.dirty and self._node is not None and self._document is not None:
            return node_source(self._node, self._document)
        if self._text == "":
            return "#\n"
        return f"# {self._text}\n"

    def __repr__(self) -> str:
        """Return a tree-oriented representation for debugging."""
        return build_semantic_repr("Comment", text=self._text)


class HorizontalRule(Element):
    """A horizontal rule line (five or more dashes).

    Args:
        rule: The rule text without its trailing newline (e.g. ``"-----"``).
    """

    def __init__(
        self,
        *,
        rule: str = "-----",
        parent: Document | Heading | Element | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._rule = rule

    @classmethod
    def from_node(
        cls,
        node: tree_sitter.Node,
        document: Document | None = None,
        *,
        parent: Document | Heading | Element | None = None,
    ) -> HorizontalRule:
        """Create a :class:`HorizontalRule` from a ``horizontal_rule`` node."""
        raw = node_source(node, document).rstrip("\n")
        elem = cls(rule=raw, parent=parent)
        elem.attach_backing(node, document)
        return elem

    @property
    def rule(self) -> str:
        """Mutable rule text without the trailing newline."""
        return self._rule

    @rule.setter
    def rule(self, value: str) -> None:
        """Set the rule text and mark this element as dirty."""
        self._rule = value
        self._mark_dirty()

    def __str__(self) -> str:
        """Render the rule line, preserving source while parse-backed and clean."""
        if not self.dirty and self._node is not None and self._document is not None:
            return node_source(self._node, self._document)
        return f"{self._rule}\n"

    def __repr__(self) -> str:
        """Return a tree-oriented representation for debugging."""
        return build_semantic_repr("HorizontalRule", rule=self._rule)


class CaptionKeyword(Element):
    """A ``#+CAPTION:`` affiliated keyword line.

    Caption keywords annotate the element immediately following them
    (typically a table or image).

    Args:
        value: The caption text following ``#+CAPTION:``.
    """

    def __init__(
        self,
        *,
        value: str,
        parent: Document | Heading | Element | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._value = value

    @classmethod
    def from_node(
        cls,
        node: tree_sitter.Node,
        document: Document | None = None,
        *,
        parent: Document | Heading | Element | None = None,
    ) -> CaptionKeyword:
        """Create a :class:`CaptionKeyword` from a ``caption_keyword`` node."""
        source = document.source if document is not None else b""
        value_node = next((c for c in node.children if c.is_named), None)
        value = node_text(value_node, source) if value_node is not None else ""
        elem = cls(value=value, parent=parent)
        elem.attach_backing(node, document)
        return elem

    @property
    def value(self) -> str:
        """Mutable caption text following ``#+CAPTION:``."""
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        """Set the caption text and mark this element as dirty."""
        self._value = value
        self._mark_dirty()

    def __str__(self) -> str:
        """Render the caption line, preserving source while parse-backed and clean."""
        if not self.dirty and self._node is not None and self._document is not None:
            return node_source(self._node, self._document)
        return f"#+CAPTION: {self._value}\n"

    def __repr__(self) -> str:
        """Return a tree-oriented representation for debugging."""
        return build_semantic_repr("CaptionKeyword", value=self._value)
