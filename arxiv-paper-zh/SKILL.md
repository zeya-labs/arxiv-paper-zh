---
name: arxiv-paper-zh
description: Download arXiv LaTeX sources and PDFs into title-based paper folders, keep English source and Chinese source trees separate, manually translate the full paper into Chinese paragraph by paragraph without machine-translation APIs, scan for likely untranslated prose, and compile paper-zh.pdf locally with tectonic. Use when asked to fetch, organize, translate, inspect, fix, or rebuild Chinese arXiv paper PDFs from source.
---

# arxiv-paper-zh

## Purpose

Use this skill to build a source-preserving Chinese paper workspace from arXiv:

```text
<papers-root>/<SimpleTitle>/
  source/
  source-zh/
  paper.pdf
  paper-zh.pdf
```

The core requirement is layout preservation. Read the paper first, translate the Chinese copy manually paragraph by paragraph, preserve LaTeX structure, and compile locally with `tectonic` so the Chinese PDF keeps the original paper layout as much as possible.

Prefer running this workflow on Linux. Linux is the recommended environment for arXiv source builds, CJK font fixes, and `tectonic` compilation.

## Workflow

### 1. Download and Scaffold

Run the downloader from this skill directory:

```bash
python {SKILL_DIR}/scripts/fetch_arxiv_papers.py \
  --dest /abs/path/to/papers-root \
  https://arxiv.org/abs/2509.23402 \
  2603.17117
```

The script downloads the original PDF, extracts the source package, verifies that `.tex` files exist, creates `source/`, and initializes `source-zh/` by copying the original source.

If a paper folder already exists, stop and inspect it. Use `--skip-existing` only when the user explicitly wants existing folders left untouched.

### 2. Read Before Translating

Before editing `source-zh/`:

- Identify the main TeX file and included section files.
- Read the full paper once, including appendix material unless the user explicitly asks for body-only translation.
- Build a small terminology map for method names, datasets, metrics, and repeated technical concepts.
- Keep model names, dataset names, benchmark names, metric names, symbols, code identifiers, and citation keys in their standard form.

Do not translate section by section blindly. The translation should reflect the paper's claims, terminology, and argument structure across the whole document.

### 3. Translate in `source-zh/`

Edit only the `source-zh/` tree. Never rewrite `source/` while producing the Chinese version.

Translate manually:

- Translate prose paragraph by paragraph into natural technical Chinese.
- Translate title, abstract, section headings, appendix headings, captions, table headers, list items, footnotes, and visible figure labels when they are part of the paper text.
- Preserve LaTeX commands, custom macros, labels, citations, references, equations, tables, figures, bibliography files, file paths, URLs, and code tokens.
- Keep proper nouns and standard technical tokens in English when that is the normal convention.
- Do not use machine-translation APIs, batch translation services, or downloaded existing translations unless the user explicitly overrides this rule.

If Chinese support is missing from the LaTeX preamble, add the smallest compatible CJK setup to the main file in `source-zh/`. For build issues, read `references/troubleshooting.md`.

### 4. Inspect for Missed English Prose

After a substantial translation pass, scan the translated tree:

```bash
python {SKILL_DIR}/scripts/inspect_tex.py scan --scope full /abs/path/to/paper-dir
```

Use `--scope body` only if the user explicitly asked not to translate appendices.

The scanner is heuristic. Fix real missed English prose. It is acceptable for the remaining hits to be proper nouns, model names, datasets, metric names, acronyms, equations, code, URLs, bibliography entries, or other text that should remain English.

### 5. Compile With Tectonic

Before building, check whether `tectonic` is available:

```bash
tectonic --version
```

If it is missing, do not stop at an instruction for the user. On Linux/macOS, self-install it to `~/.local/bin/tectonic` with the official installer:

```bash
mkdir -p ~/.local/bin
tmpdir="$(mktemp -d)"
curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net \
  -o "$tmpdir/install-tectonic.sh"
(cd "$tmpdir" && sh install-tectonic.sh)
install -m 755 "$tmpdir/tectonic" ~/.local/bin/tectonic
export PATH="$HOME/.local/bin:$PATH"
tectonic --version
```

Build the Chinese PDF:

```bash
python {SKILL_DIR}/scripts/build_translated_paper.py /abs/path/to/paper-dir
```

If the main file was detected incorrectly:

```bash
python {SKILL_DIR}/scripts/build_translated_paper.py \
  --main-tex path/relative/to/source-zh/main.tex \
  /abs/path/to/paper-dir
```

The script runs `tectonic`, copies the resulting PDF to `<paper-dir>/paper-zh.pdf`, and reports the build log location if compilation fails. If `tectonic` is missing, it attempts the same self-install automatically unless `--no-install-tectonic` is passed.

### 6. Verify

Before finishing:

- Confirm `paper.pdf` exists.
- Confirm `source/` remains unchanged unless the user explicitly requested otherwise.
- Confirm `source-zh/` contains the translated TeX.
- Confirm `paper-zh.pdf` exists and is non-empty.
- Mention any unresolved build warnings only when they matter for the user's next action.

## Translation Conventions

- Prefer concise, publication-style Chinese over literal word-for-word rendering.
- Translate "novel view" as `新视角` unless the paper uses a different meaning.
- Translate "feed-forward" as `前馈式`.
- Translate "reconstruction" as `重建` in vision/3D contexts.
- Preserve citation keys and cross-reference labels exactly.
- Shorten figure overlay labels when necessary, but keep their meaning.

## Bundled Resources

- `scripts/fetch_arxiv_papers.py`: download arXiv sources/PDFs and create the bilingual workspace.
- `scripts/inspect_tex.py`: scan translated TeX for likely missed English prose.
- `scripts/build_translated_paper.py`: compile `source-zh/` with `tectonic` and sync `paper-zh.pdf`.
- `references/troubleshooting.md`: common source and build problems.
