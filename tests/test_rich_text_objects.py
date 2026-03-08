"""Tests for rich text inline object abstractions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from org_parser.document import load_raw
from org_parser.text import (
    AngleLink,
    Bold,
    Citation,
    Code,
    CompletionCounter,
    ExportSnippet,
    FootnoteReference,
    InlineSourceBlock,
    Italic,
    LineBreak,
    PlainLink,
    PlainText,
    RadioTarget,
    RegularLink,
    RichText,
    StrikeThrough,
    Target,
    Timestamp,
    Underline,
    Verbatim,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import tree_sitter


def _find_first_paragraph_with_prefix(
    root: tree_sitter.Node,
    source: bytes,
    prefix: str,
) -> tree_sitter.Node:
    """Find first paragraph node whose text starts with *prefix*."""
    stack: list[tree_sitter.Node] = [root]
    while stack:
        node = stack.pop()
        if node.type == "paragraph":
            text = source[node.start_byte : node.end_byte].decode()
            if text.startswith(prefix):
                return node
        stack.extend(reversed(node.children))
    raise AssertionError(f"Paragraph starting with {prefix!r} not found")


def _find_first_heading_title_node_with_type(
    root: tree_sitter.Node,
    target_type: str,
) -> tree_sitter.Node:
    """Find the first heading-title child node of *target_type*."""
    stack: list[tree_sitter.Node] = [root]
    while stack:
        node = stack.pop()
        if node.type == "heading":
            for child in node.children_by_field_name("title"):
                if child.type == target_type:
                    return child
        stack.extend(reversed(node.children))
    raise AssertionError(f"Heading title node of type {target_type!r} not found")


def test_rich_text_from_paragraph_parses_inline_objects(
    example_file: Callable[[str], Path],
) -> None:
    """RichText.from_node parses mixed inline objects in paragraphs."""
    path = example_file("inline-markup-basic.org")
    source = path.read_bytes()
    tree = load_raw(path)
    paragraph = _find_first_paragraph_with_prefix(tree.root_node, source, "Markup mid-")
    rich_text = RichText.from_node(paragraph, source)

    object_types = {type(part) for part in rich_text.parts}
    assert PlainText in object_types
    assert Bold in object_types
    assert Italic in object_types
    assert Underline in object_types
    assert rich_text.dirty is False


def test_rich_text_from_nodes_parses_heading_title_objects(
    example_file: Callable[[str], Path],
) -> None:
    """RichText.from_node parses heading title inline object nodes."""
    path = example_file("export-snippet-basic.org")
    source = path.read_bytes()
    tree = load_raw(path)
    snippet = _find_first_heading_title_node_with_type(tree.root_node, "export_snippet")
    rich_text = RichText.from_node(snippet, source)
    assert len(rich_text.parts) == 1
    assert isinstance(rich_text.parts[0], ExportSnippet)


def test_rich_text_clean_str_is_verbatim_source(
    example_file: Callable[[str], Path],
) -> None:
    """Clean RichText stringification reuses verbatim source slice."""
    path = example_file("footnote-basic.org")
    source = path.read_bytes()
    tree = load_raw(path)
    paragraph = _find_first_paragraph_with_prefix(
        tree.root_node, source, "An inline foot"
    )
    rich_text = RichText.from_node(paragraph, source)
    expected = source[paragraph.start_byte : paragraph.end_byte].decode()
    assert str(rich_text) == expected


def test_rich_text_mutation_marks_dirty_and_reconstructs(
    example_file: Callable[[str], Path],
) -> None:
    """Mutations switch RichText to reconstructed rendering mode."""
    path = example_file("inline-markup-basic.org")
    source = path.read_bytes()
    tree = load_raw(path)
    paragraph = _find_first_paragraph_with_prefix(tree.root_node, source, "*bold text*")
    rich_text = RichText.from_node(paragraph, source)

    rich_text.prepend(PlainText("START "))
    rich_text.append(PlainText(" END"))
    rich_text.insert(1, PlainText("MID "))

    assert rich_text.dirty is True
    assert str(rich_text).startswith("START MID ")
    assert str(rich_text).endswith(" END")


def test_programmatic_rich_text_construction_uses_public_objects() -> None:
    """Programmatic construction with public inline object classes works."""
    rich_text = RichText(
        [
            PlainText("A "),
            Bold([PlainText("bold")]),
            PlainText(" "),
            Italic([PlainText("italic")]),
            PlainText(" "),
            Underline([PlainText("under")]),
            PlainText(" "),
            StrikeThrough([PlainText("gone")]),
            PlainText(" "),
            Verbatim("raw"),
            PlainText(" "),
            Code("x()"),
            PlainText(" "),
            CompletionCounter("2/5"),
            PlainText(" "),
            PlainLink("https", "//example.org"),
            PlainText(" "),
            AngleLink("//example.org", "https"),
            PlainText(" "),
            RegularLink("id:abc", [PlainText("desc")]),
            PlainText(" "),
            Target("anchor"),
            PlainText(" "),
            RadioTarget([PlainText("radio")]),
            PlainText(" "),
            Timestamp("<2025-01-01 Wed>"),
            PlainText(" "),
            FootnoteReference(label="a", definition=[PlainText("d")]),
            PlainText(" "),
            Citation(body="@k", style="t"),
            PlainText(" "),
            InlineSourceBlock(language="python", headers=":results", body="1+1"),
            PlainText(" "),
            ExportSnippet("html", "<b>"),
            PlainText(" "),
            LineBreak(),
        ]
    )
    expected = (
        "A *bold* /italic/ _under_ +gone+ =raw= ~x()~ [2/5] https://example.org "
        "<https://example.org> [[id:abc][desc]] <<anchor>> <<<radio>>> "
        "<2025-01-01 Wed> [fn:a:d] [cite/t:@k] src_python[:results]{1+1} "
        "@@html:<b>@@ \\\\"
    )
    assert str(rich_text) == expected
