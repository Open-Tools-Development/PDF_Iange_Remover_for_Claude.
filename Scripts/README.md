# PDF Image Remover

A small Windows desktop tool that **removes every image from PDF files while
keeping all text and the exact page layout unchanged**. The output PDFs contain
no image objects at all, so they upload to Claude AI without hitting the image
limit — perfect for reviewing the text of IEEE (or any) papers. Keep your
originals and share the image-free copy; share the original later if the figures
matter.

## What it does

- Select individual **PDF files** or a whole **folder** (optionally including
  subfolders).
- See the full list of PDFs that will be processed in the window.
- Choose an **output folder** for the cleaned copies.
- Removes all raster images; **text content and layout are untouched** and the
  result is verified to contain zero images.

## Files in this package

| File | Purpose |
|------|---------|
| `pdf_image_remover.py` | The tool (UI + image-removal logic). |
| `requirements.txt` | The one dependency (PyMuPDF). |
| `install_dependencies.bat` | Installs Python dependencies. Run this once first. |
| `run.bat` | Runs the tool with Python. |
| `build_exe.bat` | Builds a standalone `.exe` (no Python needed to run it). |

## Quick start (run with Python)

1. Install **Python 3.8+** from <https://www.python.org/downloads/> and tick
   **"Add Python to PATH"** during setup.
2. Double-click **`install_dependencies.bat`** (one time).
3. Double-click **`run.bat`** to open the tool.

In the window:
1. Click **Add PDF File(s)…** or **Add Folder…**.
2. Click **Browse…** to pick an output folder.
3. Click **Remove Images**. Cleaned files are written to the output folder.

The **"Append \_noimg"** option (on by default) names outputs like
`paper_noimg.pdf` so your originals are never overwritten.

## Build a standalone EXE (optional)

Double-click **`build_exe.bat`**. When it finishes, your program is at:

```
dist\PDFImageRemover.exe
```

Copy that `.exe` to any Windows PC and run it — no Python required.

## Notes

- Works on normal PDFs including IEEE papers. Text, tables and vector line-art
  (drawn charts) are preserved; only embedded raster images are removed.
- If `run.bat` says **PyMuPDF is missing**, run `install_dependencies.bat` first.
- If the built `.exe` ever fails to start with a *fitz/pymupdf not found* error,
  rebuild after editing `build_exe.bat` to add `--collect-all fitz` alongside
  `--collect-all pymupdf`.

## How it works (technical)

For each page the tool finds every image, marks its rectangle with a redaction
annotation that paints nothing, then applies the redaction with image-only
removal (text and line-art removal disabled). Saving with
`garbage=4, clean=True` physically discards the now-orphaned image objects, so
the file ends up with no `/Image` objects — which is why no PDF reader, and no
AI, will detect an image.
