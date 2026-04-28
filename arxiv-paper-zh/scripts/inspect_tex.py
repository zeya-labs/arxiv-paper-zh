#!/usr/bin/env python3
"""Heuristically scan translated LaTeX for likely untranslated English prose."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")
BEGIN_DOC_RE = re.compile(r"\\begin\{document\}")
END_DOC_RE = re.compile(r"\\end\{document\}")
APPENDIX_RE = re.compile(r"\\appendix\b")
BEGIN_BIB_RE = re.compile(r"\\begin\{thebibliography\}|\\bibliographystyle\{|\\bibliography\{")
BEGIN_VERBATIM_RE = re.compile(r"\\begin\{(?:verbatim|lstlisting|minted|algorithmic)\}")
END_VERBATIM_RE = re.compile(r"\\end\{(?:verbatim|lstlisting|minted|algorithmic)\}")
BEGIN_TABULAR_RE = re.compile(r"\\begin\{(?:tabular|tabularx|array)\}")
END_TABULAR_RE = re.compile(r"\\end\{(?:tabular|tabularx|array)\}")
COMMENT_RE = re.compile(r"(?<!\\)%.*$")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
ALPHA_RUN_RE = re.compile(r"[A-Za-z]{7,}")
TABULAR_SPEC_RE = re.compile(r"^[lcrpmbX|@!0-9.\s>{}<\\[\]-]+$")

STRIP_PATTERNS = [
    re.compile(r"\\(?:input|include|subfile)\{[^}]*\}"),
    re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}"),
    re.compile(r"\\(?:cite|citep|citet|citealp|ref|autoref|cref|Cref|eqref|label)\*?(?:\[[^\]]*\])?\{[^}]*\}"),
    re.compile(r"\\(?:url|path)\{[^}]*\}"),
    re.compile(r"\\href\{[^}]*\}\{[^}]*\}"),
    re.compile(r"\\(?:texttt|textsc|mathrm|mathbf|mathit|emph)\{[^}]*\}"),
    re.compile(r"\$[^$]*\$"),
    re.compile(r"\\\([^)]*\\\)"),
    re.compile(r"\\\[[\s\S]*?\\\]"),
    re.compile(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?"),
    re.compile(r"[{}\\[\]]"),
]


@dataclass(frozen=True)
class Suspect:
    path: Path
    lineno: int
    snippet: str


def source_zh_dir(paper_dir_or_source_zh: Path) -> Path:
    p = paper_dir_or_source_zh.expanduser().resolve()
    if p.name == "source-zh" and p.is_dir():
        return p
    candidate = p / "source-zh"
    if candidate.is_dir():
        return candidate
    raise FileNotFoundError(f"missing source-zh directory under {p}")


def main_tex_from_meta(src: Path) -> Path | None:
    meta = src.parent / "paper-meta.json"
    if not meta.exists():
        return None
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
        rel = Path(str(data.get("main_tex", "")))
    except Exception:
        return None
    if rel and not rel.is_absolute() and (src / rel).is_file():
        return rel
    return None


def find_main_tex(src: Path) -> Path:
    meta_main = main_tex_from_meta(src)
    if meta_main:
        return meta_main

    candidates: list[tuple[tuple[int, int, int, str], Path]] = []
    for tex_file in src.rglob("*.tex"):
        try:
            text = tex_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if r"\documentclass" not in text:
            continue
        rel = tex_file.relative_to(src)
        include_count = len(INPUT_RE.findall(text))
        candidates.append(((-include_count, len(rel.parts), len(str(rel)), str(rel)), rel))
    if not candidates:
        raise FileNotFoundError(f"no main TeX file found under {src}")
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def resolve_include(current_file: Path, raw: str, src: Path) -> Path | None:
    raw = raw.strip()
    if not raw:
        return None
    candidates = [raw]
    if not raw.lower().endswith(".tex"):
        candidates.append(raw + ".tex")
    for item in candidates:
        path = (current_file.parent / item).resolve()
        try:
            path.relative_to(src)
        except ValueError:
            continue
        if path.is_file():
            return path
    return None


def walk_tex_files(src: Path, main_tex: Path) -> list[Path]:
    root_main = (src / main_tex).resolve()
    queue = [root_main]
    seen: set[Path] = set()
    ordered: list[Path] = []

    while queue:
        cur = queue.pop(0)
        if cur in seen or not cur.exists():
            continue
        seen.add(cur)
        ordered.append(cur)
        try:
            text = cur.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in INPUT_RE.finditer(text):
            inc = resolve_include(cur, match.group(1), src)
            if inc and inc not in seen:
                queue.append(inc)
    return ordered


def relevant_lines(lines: list[str], scope: str) -> Iterable[tuple[int, str]]:
    if scope == "full":
        for idx, line in enumerate(lines, start=1):
            yield idx, line
        return

    in_doc = False
    in_verbatim = False
    in_tabular = False
    for idx, line in enumerate(lines, start=1):
        if not in_doc and BEGIN_DOC_RE.search(line):
            in_doc = True
        if not in_doc:
            continue
        if APPENDIX_RE.search(line) or BEGIN_BIB_RE.search(line) or END_DOC_RE.search(line):
            break
        if BEGIN_VERBATIM_RE.search(line):
            in_verbatim = True
        if BEGIN_TABULAR_RE.search(line):
            in_tabular = True
        if not in_verbatim and not in_tabular:
            yield idx, line
        if END_VERBATIM_RE.search(line):
            in_verbatim = False
        if END_TABULAR_RE.search(line):
            in_tabular = False


def strip_for_detection(raw: str) -> str:
    s = COMMENT_RE.sub("", raw)
    for pattern in STRIP_PATTERNS:
        s = pattern.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def is_suspect(s: str) -> bool:
    if not s or CJK_RE.search(s):
        return False
    if TABULAR_SPEC_RE.fullmatch(s):
        return False
    alpha = sum(1 for ch in s if ch.isalpha())
    if alpha < 14:
        return False
    if ALPHA_RUN_RE.search(s):
        return True
    return alpha / max(len(s), 1) > 0.45


def scan(paper_dir_or_source_zh: Path, scope: str, main_tex_override: str | None) -> list[Suspect]:
    src = source_zh_dir(paper_dir_or_source_zh)
    main_tex = Path(main_tex_override) if main_tex_override else find_main_tex(src)
    if main_tex.is_absolute() or ".." in main_tex.parts:
        raise ValueError("--main-tex must be relative to source-zh/")

    suspects: list[Suspect] = []
    for tex_file in walk_tex_files(src, main_tex):
        try:
            lines = tex_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for lineno, raw in relevant_lines(lines, scope):
            stripped = strip_for_detection(raw)
            if is_suspect(stripped):
                suspects.append(Suspect(tex_file.relative_to(src), lineno, stripped[:180]))
    return suspects


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan_p = sub.add_parser("scan")
    scan_p.add_argument("paper_dir", help="Paper directory or source-zh directory.")
    scan_p.add_argument("--scope", choices=("body", "full"), default="full")
    scan_p.add_argument("--main-tex", help="Optional main TeX path relative to source-zh/.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.cmd == "scan":
        suspects = scan(Path(args.paper_dir), args.scope, args.main_tex)
        print(f"SUSPECT_COUNT={len(suspects)}")
        for item in suspects:
            print(f"SUSPECT={item.path.as_posix()}:{item.lineno}:{item.snippet}")
        return 0
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

