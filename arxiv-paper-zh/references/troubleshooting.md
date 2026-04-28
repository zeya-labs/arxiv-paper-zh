# Troubleshooting

## No LaTeX Source

Some arXiv submissions only provide a PDF or non-TeX source bundle. The downloader must stop if no `.tex` files are found. In that case, do not create a fake translated source tree; tell the user the source-preserving workflow is not applicable.

## Main TeX File Detection

If the build script picks the wrong file, rerun it with:

```bash
python {SKILL_DIR}/scripts/build_translated_paper.py --main-tex path/to/main.tex /path/to/paper-dir
```

`--main-tex` is relative to `source-zh/`.

## Chinese Support

If a translated paper fails because CJK characters are unsupported, add a Chinese-capable LaTeX stack to the main file preamble. Prefer the smallest change compatible with the template. Common options:

```tex
\usepackage[UTF8]{ctex}
```

or, for XeLaTeX-style templates:

```tex
\usepackage{xeCJK}
\setCJKmainfont{FandolSong-Regular}
```

Do not remove the paper's required class, packages, labels, citations, figures, bibliography, or custom macros unless a build error requires a targeted fix.

## Tectonic Not Found

Install `tectonic` and confirm:

```bash
tectonic --version
```

The build script requires `tectonic` on `PATH`.

