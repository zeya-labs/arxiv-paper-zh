# arxiv-paper-zh

`arxiv-paper-zh` is an Agent Skill for producing reviewable Chinese versions of arXiv LaTeX papers. It downloads the original source and PDF, keeps the English source untouched, creates a separate translated source tree, and compiles the Chinese copy locally with `tectonic`.

The project is deliberately source-preserving. It is meant for careful paper translation work where the agent first reads the paper, builds consistent terminology, translates paragraph by paragraph, and leaves a `.tex` translation that can be inspected and revised.

## What It Does

- Downloads arXiv source packages and original PDFs.
- Creates one folder per paper using a short title-based name.
- Preserves the original source under `source/`.
- Creates the Chinese editable copy under `source-zh/`.
- Scans the translated source for likely untranslated English prose.
- Compiles the Chinese LaTeX project locally with `tectonic`.
- Writes the final Chinese PDF as `paper-zh.pdf`.

The generated workspace looks like this:

```text
papers/WorldSplat/
  source/
  source-zh/
  paper.pdf
  paper-zh.pdf
```

## Why This Exists

Many arXiv translation tools optimize for quick automatic output. This skill optimizes for a different workflow:

- local compilation instead of remote LaTeX build services;
- original and translated source trees kept side by side;
- full-paper context before translation;
- manual, paragraph-level translation by the current agent;
- no machine-translation APIs or downloaded existing translations;
- inspectable `.tex` output and reproducible `tectonic` builds.

## Installation

Clone this repository, then install the inner skill directory into your Codex skills directory:

```bash
git clone https://github.com/zeya-labs/arxiv-paper-zh.git
mkdir -p ~/.codex/skills
cp -R arxiv-paper-zh/arxiv-paper-zh ~/.codex/skills/
```

Restart Codex or reload skills if your client requires it.

## Requirements

- Python 3.10 or newer.
- Network access to `arxiv.org`.
- `tectonic` available on `PATH`.

Install `tectonic` with your preferred package manager, or see the official project for platform-specific installation instructions.

## Example Prompts

```text
Use $arxiv-paper-zh to download https://arxiv.org/abs/2509.23402 into ./papers, translate the full paper into Chinese, and compile paper-zh.pdf.
```

```text
Use $arxiv-paper-zh for 2603.17117 and 2601.00051v1. Keep source and source-zh separate, translate all sections, and build with tectonic.
```

## Direct Script Usage

The bundled scripts can also be run manually from the inner skill directory.

Download and scaffold papers:

```bash
python arxiv-paper-zh/scripts/fetch_arxiv_papers.py \
  --dest ./papers \
  https://arxiv.org/abs/2509.23402 \
  2603.17117
```

Scan a translated paper for likely untranslated English prose:

```bash
python arxiv-paper-zh/scripts/inspect_tex.py scan --scope full ./papers/WorldSplat
```

Compile the translated source:

```bash
python arxiv-paper-zh/scripts/build_translated_paper.py ./papers/WorldSplat
```

## Limitations

This workflow requires arXiv papers that provide LaTeX source. PDF-only submissions cannot be translated through this source-preserving path.

The project does not distribute paper sources, translated papers, or generated PDFs. Users are responsible for ensuring their use of paper content complies with the paper's license and applicable policies.

