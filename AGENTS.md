# AGENTS.md
Guidance for coding agents working in `tree-sitter-org`.

## Scope and Structure
- Tree-sitter grammar for Org Mode syntax.
- Root helpers:
  - Parse checks: `check.py`, `leaf_errors.py`
  - Fuzz replay: `fuzz.py`

## Repository Map
- Grammar source: `grammar.js`
- External scanner: `src/scanner.c`
- Tree-sitter corpus tests: `test/corpus/*.txt`
- Tree-sitter query files: `queries/*.scm`
- Examples/fixtures: `examples/*.org`

## Toolchain (CI-Aligned)
- Node.js: `20`
- Python: `3.12` (stdlib only; required for `check.py`, `leaf_errors.py`, `fuzz.py`)
- Tree-sitter CLI: `0.26.x`

## Setup
```bash
npm install
npm run generate
```

## Build Commands
```bash
npm run build          # tree-sitter generate && tree-sitter build
npm run generate       # regenerate parser artifacts only
tree-sitter build      # produces org.so
npm run parse -- examples/simple.org
```

Notes:
- Rebuild after edits to `grammar.js` or `src/scanner.c`.

## Test Commands
```bash
npm test
tree-sitter test
tree-sitter test --file-name test/corpus/headings.txt
tree-sitter test --file-name test/corpus/headings.txt --include "Level 1 heading"
tree-sitter test --exclude "TODO"
tree-sitter test --update   # only when intentionally updating expected trees
```

## Parse-Check Utilities (repo root)
```bash
python3 check.py "examples/*.org" "*.org"
python3 check.py examples/simple.org
python3 leaf_errors.py examples/simple.org --context 2
```
- `check.py` can be slow; allow extended timeout (~300s).

## Fuzz Sanity Checks
Use fuzzing when parser edits touch incremental parsing behavior or recovery.

### `tree-sitter fuzz` quick pass
```bash
tree-sitter fuzz --iterations 10 --edits 3
```
- Mutates corpus inputs and compares incremental parse behavior against full reparse behavior.
- Use `--include` / `--exclude` to target a corpus test title subset.
- Set `TREE_SITTER_SEED=<n>` to fix the random seed for reproducible runs.

### Capture replayable failing snapshots
```bash
tree-sitter fuzz --log-graphs --iterations 50 --edits 5 --include "heading"
```
- `--log-graphs` prints per-edit input snapshots to stdout.
- If fuzz reports an incorrect parse, copy the logged block for replay.

### Replay with `fuzz.py` (repo root)
```bash
# Paste a single fuzz log block into fuzz_input.log first
python3 fuzz.py < fuzz_input.log
python3 fuzz.py --lib-path org.so < fuzz_input.log
```
- `fuzz.py` parses snapshot logs, computes contiguous edits, replays incremental parsing, and compares S-expressions against full parses at each step.
- Exit code `0` means all steps matched, `1` means mismatch detected, `2` means malformed input/usage error.

## Generated Files (Do Not Hand-Edit nor read)
- `src/parser.c`
- `src/grammar.json`
- `src/node-types.json`
- `src/tree_sitter/*`
- `org.so`
- `tree-sitter-org.wasm`

Regenerate generated artifacts with `npm run build` or `npm run generate`.

## Code Style and Conventions
### General
- Keep diffs focused; avoid unrelated refactors.
- Follow existing naming and module boundaries.
- Preserve parser recovery behavior unless intentionally improving it.

### `grammar.js` style
- 2-space indentation.
- Semicolons required.
- Prefer single-quoted strings.
- Keep helpers small and near top-level.
- Use comments only for non-obvious scanner/grammar interactions.
- Public rules: `snake_case` (e.g., `plain_list`).
- Internal rules: leading underscore (e.g., `_object`, `_NL`).
- Token-like internals may use upper snake (`_TODO_KW`, `_PLAN_KW`).
- Use `field(...)` for meaningful named children.
- Use `prec(...)` only where ambiguity needs it.

### Scanner style (`src/scanner.c`)
- Keep token enum order aligned with `externals` in `grammar.js`.
- Prefer `static` helpers and `bool` predicates.
- Use fixed-width integer state (`uint8_t`, `uint16_t`, `int32_t`).
- Constants/macros in `UPPER_SNAKE_CASE`.
- Preserve bounds/serialization guards (`MAX_*`, `SERIALIZE_BUF_SIZE`).
- Avoid dynamic allocation unless truly necessary.
- Document subtle state-machine invariants where needed.

### Naming
- Grammar/AST node names: `snake_case`
- Scanner helpers: verb-oriented lower snake (`scan_*`, `is_*`)
- Prefer domain-specific names over generic placeholders

### Error handling
- Prefer resilient parsing and recovery over hard-fail behavior.
- Script diagnostics should be actionable and directed to stderr when appropriate.

## Agent Workflow
- Read nearby grammar/scanner code before editing.
- Run the narrowest relevant test first (single file/test/title), then broaden.
- For grammar/scanner changes:
  - Rebuild: `npm run build`
  - Run grammar tests: `tree-sitter test`
  - Run parse checks: `python3 check.py "examples/*.org" "*.org"`
