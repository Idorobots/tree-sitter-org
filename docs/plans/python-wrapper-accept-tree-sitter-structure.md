# Python Wrapper: Accept Tree-Sitter Structure As-Is

## Goal

Update the Python wrapper to consume the current Tree-Sitter node structure directly,
instead of reconstructing list and paragraph structure in a recovery pass. Keep
`Repeat` recovery in place. Rename `IndentBlock` to `Indent` and keep it as a
first-class semantic element.

## Scope

- Remove Python-side list/paragraph topology recovery.
- Parse and preserve Tree-Sitter `list`, `list_item`, and `indent` structure directly.
- Keep repeated-task (`Repeat`) conversion behavior.
- Rename public semantic class `IndentBlock` to `Indent`.

## Plan

1. Update node constants for current grammar
   - Add `LIST = "list"` and `INDENT = "indent"` in `src/org_parser/_nodes.py`.
   - Replace uses of `BLOCK` where it currently represents indentation-wrapper dispatch.

2. Rename `IndentBlock` to `Indent`
   - Rename the class in `src/org_parser/element/_structure.py`.
   - Update imports/exports and typing references in:
     - `src/org_parser/element/__init__.py`
     - `src/org_parser/document/_body.py`
     - `src/org_parser/element/_block.py`
     - `src/org_parser/element/_drawer.py`
   - Update repr/docstrings to use `Indent`.

3. Remove list/paragraph recovery from parse pipeline
   - Remove `recover_lists(...)` usage from:
     - `src/org_parser/document/_document.py`
     - `src/org_parser/document/_heading.py`
     - `src/org_parser/element/_block.py`
     - `src/org_parser/element/_drawer.py`
   - Keep affiliated keyword attachment pass.

4. Parse list hierarchy directly from parse nodes
   - Dispatch `list` to `List.from_node` in `src/org_parser/element/_dispatch.py`.
   - Ensure `ListItem.from_node` reads `body` field children directly and builds nested
     semantic elements (including `list`, `indent`, paragraph, drawers, blocks, etc.).

5. Preserve `Repeat` recovery behavior
   - Keep conversion logic in logbook processing and heading-body list scans.
   - Adjust traversal only as needed so `Repeat` detection still works with preserved
     `Indent` wrappers.

6. Simplify structure-recovery helpers
   - Refactor `src/org_parser/element/_structure_recovery.py` to focus on affiliated
     keyword attachment and recursive container traversal.
   - Remove obsolete paragraph/list run reconstruction helpers.

7. Update tests for new semantic shape
   - Revise tests in `tests/test_list_elements.py` that assume Python-side list recovery.
   - Add/adjust tests that assert:
     - direct `list` node handling,
     - `Indent` preservation as first-class nodes,
     - unchanged `Repeat` conversion,
     - affiliated keyword attachment in nested containers.

8. Validate
   - Run `poetry run task check`.
   - Run focused suites as needed:
     - `tests/test_list_elements.py`
     - `tests/test_repeat_elements.py`
     - `tests/test_affiliated_keywords.py`
     - related drawer/block tests.

## Acceptance Criteria

- Python wrapper no longer reconstructs list/paragraph topology via recovery.
- Semantic tree matches Tree-Sitter list/indent structure.
- `Indent` replaces `IndentBlock` as the public semantic element.
- `Repeat` recovery continues to function as before.
- Existing and updated tests pass.
