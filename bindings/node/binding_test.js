const assert = require("node:assert");
const { test } = require("node:test");

const Parser = require("tree-sitter");

test("can load grammar", () => {
  const parser = new Parser();
  assert.doesNotThrow(() => parser.setLanguage(require(".")));
});

// ---------------------------------------------------------------------------
// EOF without trailing newline
//
// Every element that ends with _NL should parse cleanly even when the file
// does not end with '\n'.  This suite covers the most important node types;
// each input string intentionally has no trailing newline character.
// ---------------------------------------------------------------------------

test("list item at EOF without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("- Item 0");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  const section = tree.rootNode.firstChild;
  assert.strictEqual(section.type, "zeroth_section");
  const list = section.firstChild;
  assert.strictEqual(list.type, "list");
  assert.strictEqual(list.firstChild.type, "list_item");
});

test("multiple list items, last without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("- first\n- last");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  const list = tree.rootNode.firstChild.firstChild;
  assert.strictEqual(list.type, "list");
  assert.strictEqual(list.namedChildCount, 2);
});

test("ordered list item at EOF without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("1. item");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  const list = tree.rootNode.firstChild.firstChild;
  assert.strictEqual(list.type, "list");
});

test("tagged list item at EOF without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("- tag :: content");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  const list = tree.rootNode.firstChild.firstChild;
  assert.strictEqual(list.type, "list");
});

test("list item in heading section at EOF without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("* Heading\n- item");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  assert.strictEqual(tree.rootNode.firstChild.type, "heading");
});

test("paragraph at EOF without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("some text");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  assert.strictEqual(tree.rootNode.firstChild.firstChild.type, "paragraph");
});

test("comment at EOF without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("# a comment");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  assert.strictEqual(tree.rootNode.firstChild.firstChild.type, "comment");
});

test("fixed-width line at EOF without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse(": value");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  assert.strictEqual(tree.rootNode.firstChild.firstChild.type, "fixed_width");
});

test("horizontal rule at EOF without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("-----");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  assert.strictEqual(tree.rootNode.firstChild.firstChild.type, "horizontal_rule");
});

test("special keyword at EOF without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("#+TITLE: foo");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  assert.strictEqual(tree.rootNode.firstChild.firstChild.type, "special_keyword");
});

test("babel call at EOF without trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("#+call: foo()");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  assert.strictEqual(tree.rootNode.firstChild.firstChild.type, "babel_call");
});

test("src block whose end marker has no trailing newline", () => {
  const parser = new Parser();
  parser.setLanguage(require("."));
  const tree = parser.parse("#+begin_src sh\necho hi\n#+end_src");
  assert.ok(!tree.rootNode.hasError, `unexpected error: ${tree.rootNode.toString()}`);
  assert.strictEqual(tree.rootNode.firstChild.firstChild.type, "src_block");
});
