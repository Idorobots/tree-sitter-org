#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LeafIssue:
    start_line: int
    end_line: int
    start_col: int
    end_col: int
    kind: str
    message: str


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


def extract_xml(stdout: str) -> str:
    end_tag = "</sources>"

    start = stdout.find("<?xml")
    end = stdout.rfind(end_tag)
    if start != -1 and end != -1:
        return stdout[start : end + len(end_tag)]

    start = stdout.find("<sources")
    if start != -1 and end != -1:
        return stdout[start : end + len(end_tag)]

    return ""


def is_error_tag(tag: str) -> bool:
    local = tag.rsplit("}", 1)[-1]
    return local.upper() == "ERROR"


def extract_leaf_issues(xml_text: str) -> list[LeafIssue]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    issues: list[LeafIssue] = []
    for node in root.iter():
        if not is_error_tag(node.tag):
            continue

        has_nested_error = any(is_error_tag(desc.tag) for desc in node.iter() if desc is not node)
        if has_nested_error:
            continue

        srow = int(node.attrib.get("srow", "0"))
        scol = int(node.attrib.get("scol", "0"))
        erow = int(node.attrib.get("erow", str(srow)))
        ecol = int(node.attrib.get("ecol", "0"))
        issues.append(
            LeafIssue(
                start_line=srow + 1,
                end_line=max(srow + 1, erow + 1),
                start_col=scol + 1,
                end_col=ecol + 1,
                kind="leaf_error",
                message="leaf ERROR node",
            )
        )

    return issues


def extract_ranges_from_text(stdout: str) -> list[LeafIssue]:
    issues: list[LeafIssue] = []
    for match in re.finditer(r"\(ERROR\s+\[(\d+),\s*(\d+)\]\s*-\s*\[(\d+),\s*(\d+)\]\)", stdout):
        srow = int(match.group(1))
        scol = int(match.group(2))
        erow = int(match.group(3))
        ecol = int(match.group(4))
        issues.append(
            LeafIssue(
                start_line=srow + 1,
                end_line=max(srow + 1, erow + 1),
                start_col=scol + 1,
                end_col=ecol + 1,
                kind="leaf_error",
                message="leaf ERROR node",
            )
        )
    return issues


def parse_missing_recoveries(debug_output: str) -> list[LeafIssue]:
    issues: list[LeafIssue] = []
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
            LeafIssue(
                start_line=row + 1,
                end_line=row + 1,
                start_col=col + 1,
                end_col=col + 1,
                kind="missing_recovery",
                message=symbol,
            )
        )

    return issues


def render_context(lines: list[str], start_line: int, end_line: int, context: int) -> str:
    first = max(1, start_line - context)
    last = min(len(lines), end_line + context)
    width = len(str(last))
    out: list[str] = []
    for num in range(first, last + 1):
        marker = ">" if start_line <= num <= end_line else " "
        out.append(f"{marker} {num:>{width}} | {lines[num - 1]}")
    return "\n".join(out)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show leaf parser errors with configurable line context."
    )
    parser.add_argument("file", type=Path, help="Path to file to inspect")
    parser.add_argument(
        "--context",
        type=int,
        default=2,
        help="Context lines around each leaf error (default: 2)",
    )
    parser.add_argument(
        "--check-recovery",
        action="store_true",
        help="Also report missing-token recoveries (recover_with_missing)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    file_path = args.file

    if args.context < 0:
        print("error: --context must be >= 0", file=sys.stderr)
        return 2

    if not file_path.exists() or file_path.is_dir():
        print(f"error: file not found: {file_path}", file=sys.stderr)
        return 2

    grammar_path = Path(__file__).resolve().parent

    proc = run_parse_command(file_path, grammar_path, xml=True)
    xml_text = extract_xml(proc.stdout)
    issues = extract_leaf_issues(xml_text)

    if not issues and proc.returncode != 0:
        fallback = run_parse_command(file_path, grammar_path, xml=False)
        if fallback.returncode != 0:
            issues = extract_ranges_from_text(fallback.stdout)

    if args.check_recovery and proc.returncode == 0:
        debug_proc = run_parse_command(file_path, grammar_path, xml=False, debug_mode="normal")
        issues.extend(parse_missing_recoveries(debug_proc.stdout + "\n" + debug_proc.stderr))

    issues.sort(key=lambda issue: (issue.start_line, issue.start_col, issue.kind, issue.message))

    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()

    if not issues:
        if proc.returncode == 0:
            if args.check_recovery:
                print("No leaf parser errors or missing-token recoveries found.")
            else:
                print("No leaf parser errors found.")
            return 0
        print("Parse failed but no leaf ERROR nodes were found in XML output.", file=sys.stderr)
        return 1

    leaf_error_count = sum(1 for issue in issues if issue.kind == "leaf_error")
    recovery_count = sum(1 for issue in issues if issue.kind == "missing_recovery")

    print(f"File: {file_path}")
    print(f"Leaf errors: {leaf_error_count}")
    if args.check_recovery:
        print(f"Missing-token recoveries: {recovery_count}")
    print(f"Total issues: {len(issues)}")
    print()

    for idx, issue in enumerate(issues, start=1):
        if issue.kind == "missing_recovery":
            issue_label = f"missing-token recovery: {issue.message}"
        else:
            issue_label = issue.message
        print(
            f"#{idx} lines {issue.start_line}-{issue.end_line}, "
            f"cols {issue.start_col}-{issue.end_col} - {issue_label}"
        )
        print(render_context(lines, issue.start_line, issue.end_line, args.context))
        if idx < len(issues):
            print("\n" + ("-" * 40) + "\n")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
