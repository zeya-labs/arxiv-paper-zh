#!/usr/bin/env python3
"""Download arXiv sources/PDFs and scaffold source-preserving paper workspaces."""

from __future__ import annotations

import argparse
import gzip
import html
import io
import json
import os
import re
import shutil
import sys
import tarfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


USER_AGENT = "arxiv-paper-zh/1.0"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")
DOCCLASS_RE = re.compile(r"\\documentclass")


def normalize_arxiv_id(value: str) -> str:
    token = value.strip()
    if token.lower().startswith("arxiv:"):
        token = token.split(":", 1)[1].strip()

    if token.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(token)
        path = parsed.path.rstrip("/")
        if any(part in path for part in ("/abs/", "/pdf/", "/e-print/")):
            token = path.rsplit("/", 1)[-1]
            if token.endswith(".pdf"):
                token = token[:-4]
        else:
            raise ValueError(f"unsupported arXiv URL: {value}")

    token = token.strip()
    if not token:
        raise ValueError("empty arXiv ID")
    return token


def fetch_bytes(url: str) -> tuple[bytes, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read(), dict(resp.headers.items())


def fetch_text(url: str) -> str:
    data, headers = fetch_bytes(url)
    charset = "utf-8"
    content_type = headers.get("Content-Type", "")
    match = re.search(r"charset=([^\s;]+)", content_type, re.I)
    if match:
        charset = match.group(1)
    return data.decode(charset, errors="replace")


def fetch_title_from_api(arxiv_id: str) -> str | None:
    query = urllib.parse.urlencode({"id_list": arxiv_id})
    try:
        data, _ = fetch_bytes(f"https://export.arxiv.org/api/query?{query}")
    except Exception:
        return None
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    entry = root.find("atom:entry", ATOM_NS)
    if entry is None:
        return None
    title_el = entry.find("atom:title", ATOM_NS)
    if title_el is None:
        return None
    title = " ".join(title_el.itertext()).strip()
    return re.sub(r"\s+", " ", title) or None


def fetch_title_from_abs_page(arxiv_id: str) -> str | None:
    try:
        text = fetch_text(f"https://arxiv.org/abs/{arxiv_id}")
    except Exception:
        return None

    patterns = (
        r'<meta\s+name=["\']citation_title["\']\s+content=["\'](.*?)["\']',
        r'<meta\s+content=["\'](.*?)["\']\s+name=["\']citation_title["\']',
        r"<title>\s*(.*?)\s*</title>",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if not match:
            continue
        title = html.unescape(match.group(1))
        title = re.sub(r"\s+", " ", title).strip()
        title = re.sub(r"\s*\|\s*arXiv.*$", "", title)
        title = re.sub(r"^\[[^\]]+\]\s*", "", title)
        if title:
            return title
    return None


def fetch_title(arxiv_id: str) -> str:
    title = fetch_title_from_api(arxiv_id) or fetch_title_from_abs_page(arxiv_id)
    if not title:
        raise RuntimeError(f"unable to fetch title for {arxiv_id}")
    return title


def make_folder_name(title: str, arxiv_id: str) -> str:
    short = title.split(":", 1)[0].strip() or title.strip()
    folder = re.sub(r"[^A-Za-z0-9._-]+", "-", short).strip("-._")
    if folder:
        return folder[:120].rstrip("-._")
    return re.sub(r"[^A-Za-z0-9._-]+", "-", arxiv_id).strip("-._")


def _ensure_safe_member(dest: Path, member_name: str) -> None:
    base = dest.resolve()
    target = (dest / member_name).resolve()
    if os.path.commonpath([str(base), str(target)]) != str(base):
        raise RuntimeError(f"unsafe archive member path: {member_name}")


def safe_extract_tar(data: bytes, dest: Path) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            for member in archive.getmembers():
                _ensure_safe_member(dest, member.name)
            if sys.version_info >= (3, 12):
                archive.extractall(dest, filter="data")
            else:
                archive.extractall(dest)
        return True
    except tarfile.TarError:
        return False


def safe_extract_zip(data: bytes, dest: Path) -> bool:
    buffer = io.BytesIO(data)
    if not zipfile.is_zipfile(buffer):
        return False
    dest.mkdir(parents=True, exist_ok=True)
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as archive:
        for member in archive.infolist():
            _ensure_safe_member(dest, member.filename)
        archive.extractall(dest)
    return True


def write_single_tex(data: bytes, dest: Path) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    candidates: list[bytes] = []
    try:
        candidates.append(gzip.decompress(data))
    except OSError:
        pass
    candidates.append(data)

    for candidate in candidates:
        text = candidate.decode("utf-8", errors="replace")
        if "\\documentclass" in text or "\\begin{document}" in text:
            (dest / "paper.tex").write_text(text, encoding="utf-8")
            return True
    return False


def tex_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.tex") if path.is_file())


def find_main_tex(root: Path) -> Path:
    candidates: list[tuple[tuple[int, int, int, str], Path]] = []
    for tex_file in tex_files(root):
        try:
            text = tex_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not DOCCLASS_RE.search(text):
            continue
        rel = tex_file.relative_to(root)
        include_count = len(INPUT_RE.findall(text))
        score = (-include_count, len(rel.parts), len(str(rel)), str(rel))
        candidates.append((score, rel))

    if not candidates:
        raise FileNotFoundError(f"no main TeX file with \\documentclass found under {root}")
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def extract_source_package(data: bytes, source_dir: Path) -> None:
    extracted = safe_extract_tar(data, source_dir)
    if not extracted:
        extracted = safe_extract_zip(data, source_dir)
    if not extracted:
        extracted = write_single_tex(data, source_dir)

    if not extracted or not tex_files(source_dir):
        raise RuntimeError("arXiv source package does not contain TeX files")


def create_workspace(dest_root: Path, arxiv_id: str, skip_existing: bool) -> None:
    title = fetch_title(arxiv_id)
    folder_name = make_folder_name(title, arxiv_id)
    paper_dir = dest_root / folder_name

    if paper_dir.exists():
        if skip_existing:
            print(f"[skip] {paper_dir} already exists")
            return
        raise FileExistsError(
            f"paper directory already exists: {paper_dir}. "
            "Use --skip-existing to leave it untouched."
        )

    source_dir = paper_dir / "source"
    source_zh_dir = paper_dir / "source-zh"
    pdf_path = paper_dir / "paper.pdf"

    paper_dir.mkdir(parents=True, exist_ok=False)
    try:
        source_bytes, _ = fetch_bytes(f"https://arxiv.org/e-print/{arxiv_id}")
        extract_source_package(source_bytes, source_dir)
        main_tex = find_main_tex(source_dir)

        pdf_bytes, _ = fetch_bytes(f"https://arxiv.org/pdf/{arxiv_id}.pdf")
        pdf_path.write_bytes(pdf_bytes)
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise RuntimeError("downloaded paper.pdf is empty")

        shutil.copytree(source_dir, source_zh_dir)
        metadata = {
            "arxiv_id": arxiv_id,
            "title": title,
            "main_tex": main_tex.as_posix(),
        }
        (paper_dir / "paper-meta.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(paper_dir, ignore_errors=True)
        raise

    print(f"[ok] {title}")
    print(f"     id: {arxiv_id}")
    print(f" folder: {paper_dir}")
    print(f"   main: {main_tex.as_posix()}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download arXiv sources/PDFs and scaffold source/source-zh paper folders."
    )
    parser.add_argument(
        "--dest",
        required=True,
        help="Destination root that will contain title-based paper folders.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip papers whose destination folder already exists.",
    )
    parser.add_argument("papers", nargs="+", help="arXiv IDs or arXiv URLs.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    dest_root = Path(args.dest).expanduser().resolve()
    dest_root.mkdir(parents=True, exist_ok=True)

    for item in args.papers:
        arxiv_id = normalize_arxiv_id(item)
        create_workspace(dest_root, arxiv_id, args.skip_existing)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

