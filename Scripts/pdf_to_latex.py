#!/usr/bin/env python3
"""
pdf_to_latex.py
===============
Convert an (IEEE-style) PDF into a single, self-contained LaTeX file using the
IEEEtran document class, plus a "Latex_Resource" folder of extracted figures.

Goals (per project spec):
* One .tex per PDF, named after the PDF, that compiles on Overleaf (pdfLaTeX).
* All text recovered and structured: title, authors, abstract, index terms,
  numbered sections / subsections / sub-subsections, figure & table captions,
  references and author biographies.
* Inline citations converted to \\cite{refN}; a thebibliography is embedded so
  the file compiles in a single pass (no external .bib needed).
* Figures (both embedded raster images and vector-drawn plots/diagrams) are
  extracted to Latex_Resource with unique, conflict-free names and referenced
  with \\includegraphics, matched to their captions by page where possible.

This is a best-effort text/structure recovery, not a pixel-perfect reproduction.
Equations come through as approximate plain text (a header comment says so).
"""

import os

import fitz  # PyMuPDF

from pdf_common import (
    parse_structure, extract_raster_images, extract_vector_figures,
    latex_text, safe_label,
)


_PREAMBLE = r"""%% ------------------------------------------------------------------
%% Auto-generated from "__SRC_NAME__" by PDF Image Remover (PDF -> LaTeX).
%% Author of tool: Jerry James.  Licensed under GPL-3.0.
%%
%% This file recovers the TEXT and STRUCTURE of the original PDF in a clean,
%% compilable IEEEtran form. It is NOT a pixel-perfect copy of the PDF.
%% Equations are extracted as approximate plain text and may need manual review.
%% Figures were extracted to the "Latex_Resource" folder.
%% Compile with pdfLaTeX (e.g., on Overleaf).
%% ------------------------------------------------------------------
\documentclass[journal]{IEEEtran}

\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{url}
\usepackage{cite}
\usepackage[hidelinks]{hyperref}

\graphicspath{{Latex_Resource/}{./Latex_Resource/}}

\begin{document}
"""


def _figure_float(image_file, caption_latex, label):
    return (
        "\n\\begin{figure}[!t]\n"
        "  \\centering\n"
        f"  \\includegraphics[width=\\columnwidth]{{{image_file}}}\n"
        f"  \\caption{{{caption_latex}}}\n"
        f"  \\label{{{label}}}\n"
        "\\end{figure}\n"
    )


def convert_pdf_to_latex(pdf_path, out_dir, resource_dirname="Latex_Resource"):
    """Convert ``pdf_path`` to a .tex file in ``out_dir``.

    Figures are written to ``out_dir/resource_dirname``. Returns the .tex path.
    """
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    label_stem = safe_label(stem)
    resource_dir = os.path.join(out_dir, resource_dirname)

    doc = fitz.open(pdf_path)
    try:
        structure = parse_structure(doc)
        # Extract figures: raster first, then vector-drawn, all uniquely named.
        raster = extract_raster_images(doc, resource_dir, stem)
        vector = extract_vector_figures(doc, resource_dir, stem,
                                        start_counter=0)
    finally:
        doc.close()

    # Group images by page so captions get a figure from the same page.
    images_by_page = {}
    for img in raster + vector:
        images_by_page.setdefault(img["page"], []).append(img["file"])
    used_files = set()

    def pop_image_for_page(page):
        for p in (page, page - 1, page + 1):
            lst = images_by_page.get(p)
            if lst:
                f = lst.pop(0)
                used_files.add(f)
                return f
        return None

    out = [_PREAMBLE.replace("__SRC_NAME__", os.path.basename(pdf_path))]

    # --- Title / author block ---
    title_tex = latex_text(structure["title"], citations=False) or \
        latex_text(stem, citations=False)
    out.append(f"\n\\title{{{title_tex}}}\n")

    author_tex = latex_text(structure["authors"], citations=False)
    thanks_tex = latex_text(structure["thanks"], citations=False)
    if not author_tex:
        author_tex = "Unknown Author"
    if thanks_tex:
        out.append(
            "\n\\author{%\n"
            f"  {author_tex}%\n"
            f"  \\thanks{{{thanks_tex}}}%\n"
            "}\n"
        )
    else:
        out.append(f"\n\\author{{{author_tex}}}\n")

    out.append("\n\\maketitle\n")

    # --- Abstract / index terms ---
    if structure["abstract"]:
        out.append("\n\\begin{abstract}\n")
        out.append(latex_text(structure["abstract"]) + "\n")
        out.append("\\end{abstract}\n")
    if structure["index_terms"]:
        out.append("\n\\begin{IEEEkeywords}\n")
        out.append(latex_text(structure["index_terms"], citations=False) + "\n")
        out.append("\\end{IEEEkeywords}\n")

    # --- Body elements ---
    fig_counter = 0
    for el in structure["elements"]:
        etype = el["type"]
        if etype == "section":
            out.append(f"\n\\section{{{latex_text(el['text'], citations=False)}}}\n")
        elif etype == "subsection":
            out.append(f"\n\\subsection{{{latex_text(el['text'], citations=False)}}}\n")
        elif etype == "subsubsection":
            out.append(f"\n\\subsubsection{{{latex_text(el['text'], citations=False)}}}\n")
        elif etype == "paragraph":
            out.append("\n" + latex_text(el["text"]) + "\n")
        elif etype in ("figure_caption", "table_caption", "algorithm"):
            fig_counter += 1
            cap = latex_text(el["text"])
            img = pop_image_for_page(el["page"])
            label = f"fig:{label_stem}:{fig_counter}"
            if img:
                out.append(_figure_float(img, cap, label))
            else:
                # No image available (already used / not extracted): keep caption.
                out.append("\n\\par\\textit{" + cap + "}\n")

    # --- Leftover images (e.g., author photos) ---
    leftovers = [img["file"] for img in (raster + vector)
                 if img["file"] not in used_files]
    if leftovers:
        out.append("\n\\section*{Additional Extracted Figures}\n")
        for f in leftovers:
            fig_counter += 1
            out.append(_figure_float(
                f, "Extracted figure (auto-detected).",
                f"fig:{label_stem}:extra{fig_counter}"))

    # --- Author biographies ---
    if structure["biographies"]:
        out.append("\n\\section*{Author Biographies}\n")
        for para in structure["biographies"]:
            out.append("\n" + latex_text(para) + "\n")

    # --- References (embedded bibliography) ---
    refs = structure["references"]
    if refs:
        out.append("\n\\begin{thebibliography}{" + str(len(refs)) + "}\n")
        for r in refs:
            out.append(
                f"\\bibitem{{ref{r['num']}}} {latex_text(r['text'], citations=False)}\n"
            )
        out.append("\\end{thebibliography}\n")

    out.append("\n\\end{document}\n")

    tex_path = os.path.join(out_dir, f"{stem}.tex")
    with open(tex_path, "w", encoding="utf-8") as fh:
        fh.write("".join(out))

    return tex_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        print(convert_pdf_to_latex(sys.argv[1], sys.argv[2]))
    else:
        print("usage: pdf_to_latex.py <input.pdf> <output_dir>")
