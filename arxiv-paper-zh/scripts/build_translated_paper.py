#!/usr/bin/env python3
"""Compile source-zh with tectonic and copy the result to paper-zh.pdf."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def find_main_tex(source_zh_dir: Path) -> Path:
    meta = source_zh_dir.parent / "paper-meta.json"
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            rel = Path(str(data.get("main_tex", "")))
            if rel and (source_zh_dir / rel).is_file():
                return rel
        except Exception:
            pass

    preferred = source_zh_dir / "paper.tex"
    if preferred.is_file():
        return preferred.relative_to(source_zh_dir)

    candidates: list[tuple[tuple[int, int, int, str], Path]] = []
    for tex_file in source_zh_dir.rglob("*.tex"):
        try:
            text = tex_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if r"\documentclass" not in text:
            continue
        rel = tex_file.relative_to(source_zh_dir)
        include_count = text.count(r"\input") + text.count(r"\include")
        score = (-include_count, len(rel.parts), len(str(rel)), str(rel))
        candidates.append((score, rel))

    if not candidates:
        raise FileNotFoundError(f"no main TeX file found under {source_zh_dir}")

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def require_tectonic() -> str:
    executable = shutil.which("tectonic")
    if executable:
        return executable
    raise FileNotFoundError(
        "tectonic was not found on PATH. Install tectonic and rerun this script."
    )


def run_tectonic(source_zh_dir: Path, main_tex: Path, build_dir: Path, keep_intermediates: bool) -> None:
    executable = require_tectonic()
    build_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        executable,
        "--keep-logs",
        "--outdir",
        str(build_dir),
        main_tex.as_posix(),
    ]
    if keep_intermediates:
        cmd.insert(1, "--keep-intermediates")

    print(f"[build] {' '.join(cmd)}")
    try:
        subprocess.run(cmd, cwd=source_zh_dir, check=True)
    except subprocess.CalledProcessError as exc:
        log_path = build_dir / f"{main_tex.stem}.log"
        if log_path.exists():
            print(f"[log] {log_path}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc


def build_one_paper(paper_dir: Path, main_tex_override: str | None, keep_intermediates: bool) -> None:
    paper_dir = paper_dir.expanduser().resolve()
    source_zh_dir = paper_dir / "source-zh"
    if not source_zh_dir.is_dir():
        raise FileNotFoundError(f"missing source-zh directory: {source_zh_dir}")

    main_tex = Path(main_tex_override) if main_tex_override else find_main_tex(source_zh_dir)
    if main_tex.is_absolute() or ".." in main_tex.parts:
        raise ValueError("--main-tex must be relative to source-zh/")
    if not (source_zh_dir / main_tex).is_file():
        raise FileNotFoundError(f"missing main TeX file: {source_zh_dir / main_tex}")

    build_dir = source_zh_dir / ".build-zh"
    run_tectonic(source_zh_dir, main_tex, build_dir, keep_intermediates)

    built_pdf = build_dir / f"{main_tex.stem}.pdf"
    if not built_pdf.exists() or built_pdf.stat().st_size == 0:
        raise FileNotFoundError(f"expected non-empty output PDF not found: {built_pdf}")

    target_pdf = paper_dir / "paper-zh.pdf"
    shutil.copy2(built_pdf, target_pdf)
    print(f"[ok] {target_pdf}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile translated arXiv paper sources with tectonic and refresh paper-zh.pdf."
    )
    parser.add_argument(
        "--main-tex",
        help="Optional path to the main TeX file, relative to source-zh/.",
    )
    parser.add_argument(
        "--keep-intermediates",
        action="store_true",
        help="Keep tectonic intermediate files in source-zh/.build-zh.",
    )
    parser.add_argument(
        "paper_dirs",
        nargs="+",
        help="One or more paper directories that contain source-zh/.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    for item in args.paper_dirs:
        build_one_paper(Path(item), args.main_tex, args.keep_intermediates)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

