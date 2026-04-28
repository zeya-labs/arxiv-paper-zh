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

This skill recommends Linux and uses `tectonic` for local PDF compilation. The build script will try to install `tectonic` automatically to `~/.local/bin/tectonic` on Linux/macOS when it is missing.

Manual install:

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

If automatic installation is not allowed in the current environment, run the build script with `--no-install-tectonic` and install `tectonic` through the system package manager instead.
