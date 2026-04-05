#!/usr/bin/env python3

import argparse
import glob
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParseErrorSnippet:
    start_line: int
    end_line: int
    message: str
    snippet: str


@dataclass
class FileResult:
    path: str
    passing: bool
    errors: list[ParseErrorSnippet]


@dataclass
class RecoveryIssue:
    start_line: int
    start_col: int
    symbol: str


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def is_option_error(stdout: str, stderr: str) -> bool:
    text = (stdout + "\n" + stderr).lower()
    return (
        "unexpected argument" in text
        or "unrecognized option" in text
        or "unknown option" in text
    )


def run_parse_command(
    file_path: Path,
    grammar_path: Path,
    xml: bool,
    debug_mode: str | None = None,
) -> subprocess.CompletedProcess[str]:
    file_arg = str(file_path.resolve())
    org_so = grammar_path / "org.so"
    xml_flag = ["--xml"] if xml else []
    debug_flag = ["-d", debug_mode] if debug_mode else []

    attempts: list[tuple[list[str], Path]] = [
        (["tree-sitter", "parse", *xml_flag, *debug_flag, "--grammar-path", str(grammar_path), file_arg], Path.cwd()),
        (["tree-sitter", "parse", *xml_flag, *debug_flag, "-p", str(grammar_path), file_arg], Path.cwd()),
    ]

    if org_so.exists():
        attempts.append(
            (
                ["tree-sitter", "parse", *xml_flag, *debug_flag, "--lib-path", str(org_so), "--lang-name", "org", file_arg],
                Path.cwd(),
            )
        )

    attempts.append((["tree-sitter", "parse", *xml_flag, *debug_flag, file_arg], grammar_path))

    last_proc: subprocess.CompletedProcess[str] | None = None
    for cmd, cwd in attempts:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))
        last_proc = proc
        if not is_option_error(proc.stdout, proc.stderr):
            return proc

    assert last_proc is not None
    return last_proc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Org files for parser errors."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more files or glob patterns",
    )
    parser.add_argument(
        "--check-recovery",
        action="store_true",
        help="Also fail on missing-token recoveries (recover_with_missing)",
    )
    return parser.parse_args()


def expand_inputs(args: list[str]) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    missing: list[str] = []
    seen: set[Path] = set()

    for arg in args:
        matches = glob.glob(arg, recursive=True) if glob.has_magic(arg) else [arg]
        if not matches:
            missing.append(arg)
            continue

        for match in matches:
            p = Path(match)
            if not p.exists():
                missing.append(match)
                continue
            if p.is_dir():
                continue
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            paths.append(p)

    return paths, missing


def extract_xml(stdout: str) -> str:
    start = stdout.find("<?xml")
    end_tag = "</sources>"
    end = stdout.rfind(end_tag)
    if start == -1 or end == -1:
        return ""
    return stdout[start : end + len(end_tag)]


def extract_diagnostic(stdout: str, stderr: str) -> str:
    text = (stdout + "\n" + stderr).strip()
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if "Parse:" in line and "(" in line and line.endswith(")"):
            match = re.search(r"\((.+)\)$", line)
            if match:
                msg = match.group(1).strip()
                return "" if msg.startswith("ERROR ") else msg

    for line in reversed(lines):
        if "error:" in line.lower() or "unknown option" in line.lower() or "unrecognized option" in line.lower():
            return line
    return ""


def parse_error_ranges_from_text(parse_output: str) -> set[tuple[int, int]]:
    ranges: set[tuple[int, int]] = set()
    for match in re.finditer(r"\(ERROR\s+\[(\d+),\s*\d+\]\s*-\s*\[(\d+),\s*\d+\]\)", parse_output):
        srow = int(match.group(1))
        erow = int(match.group(2))
        start_line = srow + 1
        end_line = max(start_line, erow + 1)
        ranges.add((start_line, end_line))
    return ranges


def merge_ranges(ranges: set[tuple[int, int]]) -> list[tuple[int, int]]:
    merged_ranges: list[list[int]] = []
    for start_line, end_line in sorted(ranges):
        if not merged_ranges or start_line > merged_ranges[-1][1] + 1:
            merged_ranges.append([start_line, end_line])
        else:
            merged_ranges[-1][1] = max(merged_ranges[-1][1], end_line)
    return [(start, end) for start, end in merged_ranges]


def build_snippet(lines: list[str], start_line: int, end_line: int, context: int = 2) -> str:
    start = max(1, start_line - context)
    end = min(len(lines), end_line + context)
    return "\n".join(lines[start - 1 : end])


def parse_missing_recoveries(debug_output: str) -> list[RecoveryIssue]:
    issues: list[RecoveryIssue] = []
    seen: set[tuple[int, int, str]] = set()
    row = 0
    col = 0

    for raw in debug_output.splitlines():
        line = ANSI_ESCAPE_RE.sub("", raw).strip()
        pos_match = re.search(r"process version:\d+.*row:(\d+), col:(\d+)", line)
        if pos_match:
            row = int(pos_match.group(1))
            col = int(pos_match.group(2))
            continue

        rec_match = re.search(r"recover_with_missing symbol:([^,\s]+)", line)
        if not rec_match:
            continue

        symbol = rec_match.group(1)
        key = (row, col, symbol)
        if key in seen:
            continue
        seen.add(key)

        issues.append(
            RecoveryIssue(
                start_line=row + 1,
                start_col=col + 1,
                symbol=symbol,
            )
        )

    return issues


def run_parse(file_path: Path, grammar_path: Path, check_recovery: bool) -> FileResult:
    try:
        proc = run_parse_command(file_path, grammar_path, xml=True)
    except FileNotFoundError:
        return FileResult(
            path=str(file_path),
            passing=False,
            errors=[
                ParseErrorSnippet(
                    start_line=1,
                    end_line=1,
                    message="tree-sitter CLI not found in PATH",
                    snippet="",
                )
            ],
        )

    xml_text = extract_xml(proc.stdout)
    diagnostic = extract_diagnostic(proc.stdout, proc.stderr)

    file_lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    snippets: list[ParseErrorSnippet] = []
    ranges: set[tuple[int, int]] = set()

    if xml_text:
        try:
            root = ET.fromstring(xml_text)
            for node in root.iter("ERROR"):
                srow = int(node.attrib.get("srow", "0"))
                erow = int(node.attrib.get("erow", str(srow)))
                start_line = srow + 1
                end_line = max(start_line, erow + 1)
                ranges.add((start_line, end_line))
        except ET.ParseError:
            ranges = set()

    if not ranges and proc.returncode != 0:
        fallback_proc = run_parse_command(file_path, grammar_path, xml=False)
        fallback_ranges = parse_error_ranges_from_text(fallback_proc.stdout)
        if fallback_ranges:
            ranges = fallback_ranges
        if not diagnostic:
            diagnostic = extract_diagnostic(fallback_proc.stdout, fallback_proc.stderr)

    for start_line, end_line in merge_ranges(ranges):
        snippets.append(
            ParseErrorSnippet(
                start_line=start_line,
                end_line=end_line,
                message=diagnostic,
                snippet=build_snippet(file_lines, start_line, end_line),
            )
        )

    if check_recovery and not snippets and proc.returncode == 0:
        debug_proc = run_parse_command(file_path, grammar_path, xml=False, debug_mode="normal")
        recoveries = parse_missing_recoveries(debug_proc.stdout + "\n" + debug_proc.stderr)
        for recovery in recoveries:
            snippets.append(
                ParseErrorSnippet(
                    start_line=recovery.start_line,
                    end_line=recovery.start_line,
                    message=f"missing-token recovery at col {recovery.start_col}: {recovery.symbol}",
                    snippet=build_snippet(file_lines, recovery.start_line, recovery.start_line),
                )
            )

    if not snippets and proc.returncode != 0:
        fallback = diagnostic or "Parser command failed"
        snippets.append(
            ParseErrorSnippet(
                start_line=1,
                end_line=1,
                message=fallback,
                snippet="\n".join(file_lines[: min(len(file_lines), 5)]),
            )
        )

    passing = len(snippets) == 0 and proc.returncode == 0
    return FileResult(path=str(file_path), passing=passing, errors=snippets)


def main() -> int:
    args = parse_args()
    inputs = args.inputs
    files, missing = expand_inputs(inputs)
    if missing:
        for m in missing:
            print(f"warning: no matches for '{m}'", file=sys.stderr)

    if not files:
        print("No files to check.", file=sys.stderr)
        return 2

    grammar_path = Path(__file__).resolve().parent

    results = [run_parse(path, grammar_path, check_recovery=args.check_recovery) for path in files]
    passing = sum(1 for r in results if r.passing)
    total = len(results)

    print(f"{passing}/{total} files passing")

    failing = [r for r in results if not r.passing]
    if not failing:
        return 0

    print()
    for idx, result in enumerate(failing):
        print(f"# {result.path}:")
        print()
        for err in result.errors:
            line_label = f"line {err.start_line}" if err.start_line == err.end_line else f"lines {err.start_line}-{err.end_line}"
            if err.message:
                print(f"{line_label}: {err.message}")
            else:
                print(line_label)
            print("```")
            print(err.snippet)
            print("```")
            print()

        if idx < len(failing) - 1:
            print()

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
