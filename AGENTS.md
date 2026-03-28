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
- Language metadata: `tree-sitter.json`
- Tree-sitter corpus tests: `test/corpus/*.txt`
- Tree-sitter query files: `queries/*.scm`
- Examples/fixtures: `examples/*.org`
- Language bindings: `bindings/node/`, `bindings/python/`, `bindings/c/`
- Python build entry point: `setup.py`, `pyproject.toml`

## Toolchain (CI-Aligned)
- Node.js: `20`
- Python: `3.12` (stdlib only for `check.py`, `leaf_errors.py`; `tree-sitter` package for `fuzz.py`)
- Tree-sitter CLI: `0.26.x`

## Setup
```bash
npm install
tree-sitter generate
```

## Build Commands
```bash
tree-sitter generate        # regenerate src/parser.c and related artifacts
tree-sitter build           # compile org.so from src/parser.c + src/scanner.c
tree-sitter parse examples/simple.org
```

Notes:
- Rebuild (`tree-sitter generate && tree-sitter build`) after any edit to `grammar.js` or `src/scanner.c`.
- `npm run build` and `npm run generate` **no longer exist** in `package.json`; use the CLI directly.

## Test Commands

### Corpus tests (primary)
```bash
tree-sitter test                                                  # all corpus tests
tree-sitter test --file-name test/corpus/headings.txt            # single corpus file
tree-sitter test --file-name test/corpus/headings.txt --include "Level 1 heading"  # single test
tree-sitter test --exclude "TODO"                                 # exclude by title pattern
tree-sitter test --update                                         # update expected output (intentional only)
```

### Corpus files by topic
| File | Topic |
|---|---|
| `citations.txt` | `[cite:...]` syntax |
| `clocks.txt` | `CLOCK:` entries |
| `comments.txt` | `#` and `# ` comment lines |
| `document.txt` | Top-level document structure |
| `drawers.txt` | `:DRAWER:` ... `:END:` |
| `entities.txt` | `\entity` references |
| `error_recovery.txt` | Parser error recovery behavior |
| `fixed_width.txt` | `: ` fixed-width lines |
| `footnotes.txt` | `[fn:label]` definitions and references |
| `greater_blocks.txt` | `#+begin_NAME` ... `#+end_NAME` |
| `headings.txt` | `*` headings, TODO states, tags |
| `keywords.txt` | `#+KEYWORD:` lines |
| `lesser_blocks.txt` | `#+begin_src`, `#+begin_example`, etc. |
| `links.txt` | `[[link][desc]]` syntax |
| `lists.txt` | Unordered, ordered, description lists |
| `markup.txt` | `*bold*`, `/italic/`, `~code~`, etc. |
| `objects.txt` | Inline objects (macros, targets, timestamps) |
| `planning.txt` | `SCHEDULED:`, `DEADLINE:`, `CLOSED:` |
| `scripts.txt` | Inline babel/src calls |
| `sections.txt` | Section containment and zeroth section |
| `tables.txt` | `|`-delimited org tables |
| `timestamps.txt` | `<date>` and `[date]` formats |

### Node binding test
```bash
node --test bindings/node/binding_test.js    # smoke test via npm test
npm test
```

### Python binding test
```bash
python3 -m pytest bindings/python/tests/
```

## Parse-Check Utilities (repo root)
```bash
python3 check.py "examples/*.org" "*.org"
python3 check.py examples/simple.org
python3 leaf_errors.py examples/simple.org --context 2
```
- `check.py` can be slow; allow extended timeout (~300s).
- Both scripts print diagnostics to stderr and exit non-zero on error nodes.

## Fuzz Sanity Checks
Use fuzzing when parser edits touch incremental parsing behavior or recovery.

### `tree-sitter fuzz` quick pass
```bash
tree-sitter fuzz --iterations 10 --edits 3
```
- Mutates corpus inputs and compares incremental parse behavior against full reparse.
- Use `--include` / `--exclude` to target a corpus test title subset.
- Set `TREE_SITTER_SEED=<n>` to fix the random seed for reproducible runs.
- CI only runs the fuzz job when `src/scanner.c` changes; grammar-only changes are not fuzzed in CI — run locally if your grammar change could affect incremental parsing.

### Capture replayable failing snapshots
```bash
tree-sitter fuzz --log-graphs --iterations 50 --edits 5 --include "heading"
```
- `--log-graphs` prints per-edit input snapshots to stdout; copy a block for replay.

### Replay with `fuzz.py` (repo root)
```bash
python3 fuzz.py < fuzz_input.log
python3 fuzz.py --lib-path org.so < fuzz_input.log
```
- Parses snapshot logs, replays incremental edits, and compares S-expressions against full parses.
- Exit `0` = all steps matched; `1` = mismatch; `2` = malformed input.

## Generated Files (Do Not Hand-Edit or Read)
- `src/parser.c`, `src/grammar.json`, `src/node-types.json`, `src/tree_sitter/`
- `org.so`, `tree-sitter-org.wasm`
- `prebuilds/`

Regenerate with `tree-sitter generate && tree-sitter build`.

## Code Style and Conventions

### Indentation (from `.editorconfig`)
| File type | Style | Size |
|---|---|---|
| `.js`, `.scm`, `.json`, `.toml`, `.yml` | spaces | 2 |
| `.c`, `.cc`, `.h`, `.py`, `.pyi` | spaces | 4 |
| `Makefile` | tabs | 8 |

### `grammar.js`
- 2-space indentation; semicolons required; single-quoted strings.
- Keep helpers small and near top-level.
- Comments only for non-obvious scanner/grammar interactions.
- Public rules: `snake_case` (e.g., `plain_list`).
- Internal rules: leading underscore (e.g., `_object`, `_NL`).
- Token-like internals may use upper snake (`_TODO_KW`, `_PLAN_KW`).
- Use `field(...)` for meaningful named children.
- Use `prec(...)` only where ambiguity requires it.

### `queries/highlights.scm`
- More-specific patterns come first; fallback patterns follow.
- Duplicate capture pairs (specific + fallback) are intentional — do not collapse them.

### `src/scanner.c`
- Keep `TokenType` enum order aligned with `externals` in `grammar.js`.
- Prefer `static` helpers and `bool` predicates.
- Use fixed-width integer state (`uint8_t`, `uint16_t`, `int32_t`).
- Constants/macros in `UPPER_SNAKE_CASE`.
- Preserve bounds/serialization guards (`MAX_*`, `SERIALIZE_BUF_SIZE`).
- Avoid dynamic allocation unless truly necessary.
- Document subtle state-machine invariants.

### Naming
- Grammar/AST node names: `snake_case`
- Scanner helpers: verb-oriented lower snake (`scan_*`, `is_*`)
- Prefer domain-specific names over generic placeholders.

### Error Handling
- Prefer resilient parsing and recovery over hard-fail behavior.
- Script diagnostics should be actionable and directed to stderr.

## Agent Workflow
- Read nearby grammar/scanner code before editing.
- Run the narrowest relevant test first (single `--include` title), then broaden to the corpus file, then `tree-sitter test`.
- For grammar/scanner changes:
  1. Rebuild: `tree-sitter generate && tree-sitter build`
  2. Run targeted corpus test: `tree-sitter test --file-name test/corpus/<topic>.txt`
  3. Run full corpus: `tree-sitter test`
  4. Run parse checks: `python3 check.py "examples/*.org" "*.org"`
- CI path filters cover `grammar.js`, `src/**`, `test/**`, `bindings/**`, `tree-sitter.json`. Build-system-only changes (`CMakeLists.txt`, `Makefile`, `setup.py`) do **not** trigger CI on push to `main`.
