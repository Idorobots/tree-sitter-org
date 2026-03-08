"""Tests for semantic plain-list abstractions."""

from __future__ import annotations

from org_parser import loads
from org_parser.element import Drawer, List, ListItem, ListItemContinuation, QuoteBlock
from org_parser.text import RichText


def test_document_body_parses_plain_list_with_item_features() -> None:
    """Document body parses list items with metadata and body elements."""
    document = loads(
        "1. [@5] [X] Build release [1/2]\n"
        "  Continue with notes\n"
        "  #+begin_quote\n"
        "  quoted\n"
        "  #+end_quote\n"
    )

    assert isinstance(document.body[0], List)
    parsed = document.body[0]
    assert len(parsed.items) == 1

    item = parsed.items[0]
    assert item.ordered_counter == "1"
    assert item.bullet == "."
    assert item.counter_set == "5"
    assert item.checkbox == "X"
    assert item.first_line is not None
    assert str(item.first_line) == "Build release [1/2]"
    assert isinstance(item.body[0], ListItemContinuation)
    assert isinstance(item.body[1], QuoteBlock)
    assert item.parent is parsed
    assert item.body[0].parent is item
    assert item.body[1].parent is item


def test_heading_and_drawer_bodies_support_plain_list_elements() -> None:
    """Heading and drawer body extraction return dedicated list elements."""
    document = loads("* H\n- top\n:NOTE:\n- nested\n:END:\n")

    heading = document.children[0]
    assert isinstance(heading.body[0], List)
    assert isinstance(heading.body[1], Drawer)
    drawer = heading.body[1]
    assert isinstance(drawer.body[0], List)


def test_list_item_mutation_marks_list_and_document_dirty() -> None:
    """Mutating list-item first-line content bubbles dirty state upwards."""
    document = loads("- old\n")
    assert isinstance(document.body[0], List)
    parsed = document.body[0]
    item = parsed.items[0]

    item.first_line = RichText("new")

    assert item.dirty is True
    assert parsed.dirty is True
    assert document.dirty is True
    assert str(parsed) == "- new\n"


def test_continuation_content_mutation_bubbles_to_item_and_list() -> None:
    """Mutating continuation rich text marks owning item/list/document dirty."""
    document = loads("- one\n  next\n")
    assert isinstance(document.body[0], List)
    parsed = document.body[0]
    item = parsed.items[0]
    assert isinstance(item.body[0], ListItemContinuation)
    continuation = item.body[0]

    continuation.content.text = "changed"

    assert continuation.dirty is True
    assert item.dirty is True
    assert parsed.dirty is True
    assert document.dirty is True
    assert str(parsed) == "- one\n  changed\n"


def test_list_append_item_supports_mutation_and_adoption() -> None:
    """Appending a new item marks list dirty and adopts ownership."""
    document = loads("- first\n")
    assert isinstance(document.body[0], List)
    parsed = document.body[0]

    parsed.append_item(
        ListItem(
            bullet="-",
            first_line=RichText("second"),
        )
    )

    assert len(parsed.items) == 2
    assert parsed.items[1].parent is parsed
    assert parsed.dirty is True
    assert document.dirty is True
    assert str(parsed) == "- first\n- second\n"
