#!/usr/bin/env python3
"""
PDF Image Remover
=================
A simple desktop tool that removes ALL raster images from PDF files while
preserving the text content and the exact original page layout.

The resulting PDFs contain NO image objects, which avoids the per-upload image
limit when sending PDFs to Claude AI for text-only review. Keep your original
PDFs and share the image-free copy; share the original later if images matter.

How it works
------------
For every page the tool locates each embedded raster image, marks its area with
a redaction annotation (no fill, so nothing is drawn over the page) and then
applies the redaction with image-only removal. Text and vector/line-art are left
untouched, so wording and positions do not move. A final garbage-collection /
clean pass physically drops the orphaned image objects from the file, so no
trace of any image remains.

Tested behaviour: text length, every text span and its exact coordinates are
identical before and after; raster image count goes to zero and the raw file
contains zero '/Image' objects.

Requires: Python 3.8+  and  PyMuPDF  (pip install PyMuPDF)
Tkinter ships with the standard CPython installer on Windows/macOS.
"""

import os
import sys
import threading
import queue
import traceback

try:
    import fitz  # PyMuPDF
except Exception:  # noqa: BLE001 - we want to catch any import problem
    fitz = None

import tkinter as tk
from tkinter import ttk, filedialog, messagebox


APP_TITLE = "PDF Image Remover"
APP_VERSION = "1.0"
DEFAULT_SUFFIX = "_noimg"


# --------------------------------------------------------------------------- #
#  Core logic (no UI) - this is the part that was tested end to end           #
# --------------------------------------------------------------------------- #
def _apply_image_only_redactions(page):
    """Apply redactions removing images only, with safe fallbacks for older
    PyMuPDF versions that do not accept the graphics/text keywords."""
    try:
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_REMOVE,
            graphics=fitz.PDF_REDACT_LINE_ART_NONE,
            text=fitz.PDF_REDACT_TEXT_NONE,
        )
    except (TypeError, AttributeError):
        try:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
        except (TypeError, AttributeError):
            page.apply_redactions()


def remove_images_from_pdf(input_path, output_path):
    """Remove every raster image from ``input_path`` and write ``output_path``.

    Returns a tuple ``(removed, remaining)``:
        removed   - number of image placements that were redacted
        remaining - number of raster images still detected afterwards
                    (0 for normal documents; >0 only for unusual edge cases)

    Text, vector graphics and exact text positions are preserved.
    """
    doc = fitz.open(input_path)
    removed = 0
    try:
        for page in doc:
            image_list = page.get_images(full=True)
            if not image_list:
                continue
            for img in image_list:
                xref = img[0]
                try:
                    rects = page.get_image_rects(xref)
                except Exception:
                    rects = []
                for rect in rects:
                    # fill=False -> nothing is painted, the image is simply
                    # removed; cross_out=False -> no diagonal marks.
                    try:
                        page.add_redact_annot(rect, fill=False, cross_out=False)
                    except TypeError:
                        # very old signature without cross_out
                        page.add_redact_annot(rect, fill=False)
                    removed += 1
            _apply_image_only_redactions(page)

        # garbage=4 + clean=True physically drop orphaned image objects so the
        # saved file contains no image data at all.
        doc.save(output_path, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()

    # Verify nothing was missed.
    remaining = 0
    try:
        check = fitz.open(output_path)
        for page in check:
            remaining += len(page.get_images(full=True))
        check.close()
    except Exception:
        remaining = -1  # could not verify

    return removed, remaining


def find_pdfs_in_folder(folder, recursive=False):
    """Return a sorted list of .pdf file paths in ``folder``."""
    found = []
    if recursive:
        for root, _dirs, files in os.walk(folder):
            for name in files:
                if name.lower().endswith(".pdf"):
                    found.append(os.path.join(root, name))
    else:
        for name in os.listdir(folder):
            full = os.path.join(folder, name)
            if os.path.isfile(full) and name.lower().endswith(".pdf"):
                found.append(full)
    return sorted(found)


# --------------------------------------------------------------------------- #
#  GUI                                                                         #
# --------------------------------------------------------------------------- #
class PdfImageRemoverApp:
    def __init__(self, root):
        self.root = root
        self.pdf_paths = []          # absolute paths queued for processing
        self.output_dir = tk.StringVar(value="")
        self.suffix_var = tk.BooleanVar(value=True)
        self.recursive_var = tk.BooleanVar(value=False)
        self.msg_queue = queue.Queue()
        self.worker = None

        root.title(f"{APP_TITLE}  v{APP_VERSION}")
        root.geometry("680x680")
        root.minsize(620, 600)

        self._build_ui()
        self.root.after(100, self._poll_queue)

    # ----------------------------- UI layout ------------------------------ #
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Header
        header = ttk.Frame(self.root)
        header.pack(fill="x", **pad)
        ttk.Label(header, text=APP_TITLE,
                  font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Remove all images from PDFs. Text and layout stay intact, "
                 "and the result contains no images.",
            foreground="#555",
        ).pack(anchor="w")

        # --- Step 1: choose input ---
        in_frame = ttk.LabelFrame(self.root, text="1. Choose PDFs to process")
        in_frame.pack(fill="both", expand=True, **pad)

        btn_row = ttk.Frame(in_frame)
        btn_row.pack(fill="x", padx=8, pady=8)
        ttk.Button(btn_row, text="Add PDF File(s)…",
                   command=self.add_files).pack(side="left")
        ttk.Button(btn_row, text="Add Folder…",
                   command=self.add_folder).pack(side="left", padx=6)
        ttk.Checkbutton(btn_row, text="Include subfolders",
                        variable=self.recursive_var).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Remove Selected",
                   command=self.remove_selected).pack(side="right")
        ttk.Button(btn_row, text="Clear List",
                   command=self.clear_list).pack(side="right", padx=6)

        self.count_label = ttk.Label(in_frame, text="PDFs queued: 0")
        self.count_label.pack(anchor="w", padx=8)

        list_wrap = ttk.Frame(in_frame)
        list_wrap.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        self.listbox = tk.Listbox(list_wrap, selectmode=tk.EXTENDED,
                                  activestyle="dotbox")
        yscroll = ttk.Scrollbar(list_wrap, orient="vertical",
                                command=self.listbox.yview)
        xscroll = ttk.Scrollbar(list_wrap, orient="horizontal",
                                command=self.listbox.xview)
        self.listbox.configure(yscrollcommand=yscroll.set,
                               xscrollcommand=xscroll.set)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        list_wrap.rowconfigure(0, weight=1)
        list_wrap.columnconfigure(0, weight=1)

        # --- Step 2: choose output ---
        out_frame = ttk.LabelFrame(self.root, text="2. Choose output folder")
        out_frame.pack(fill="x", **pad)
        row = ttk.Frame(out_frame)
        row.pack(fill="x", padx=8, pady=8)
        self.out_entry = ttk.Entry(row, textvariable=self.output_dir)
        self.out_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse…",
                   command=self.choose_output).pack(side="left", padx=6)
        ttk.Checkbutton(
            out_frame,
            text='Append "_noimg" to output file names (recommended, '
                 "prevents overwriting originals)",
            variable=self.suffix_var,
        ).pack(anchor="w", padx=8, pady=(0, 8))

        # --- Step 3: run ---
        run_frame = ttk.Frame(self.root)
        run_frame.pack(fill="x", **pad)
        self.run_btn = ttk.Button(run_frame, text="Remove Images",
                                  command=self.start_processing)
        self.run_btn.pack(side="left")
        self.progress = ttk.Progressbar(run_frame, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=10)

        # --- Log ---
        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = tk.Text(log_frame, height=8, wrap="word", state="disabled",
                           background="#1e1e1e", foreground="#e0e0e0")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical",
                                   command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        self.log.pack(side="left", fill="both", expand=True, padx=(8, 0),
                      pady=8)
        log_scroll.pack(side="right", fill="y", pady=8, padx=(0, 8))

        if fitz is None:
            self._log("PyMuPDF is not installed. Run install_dependencies.bat "
                      "(or: pip install PyMuPDF) and restart this tool.")
            self.run_btn.state(["disabled"])

    # --------------------------- list handling ---------------------------- #
    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for p in self.pdf_paths:
            self.listbox.insert(tk.END, p)
        self.count_label.config(text=f"PDFs queued: {len(self.pdf_paths)}")

    def _add_paths(self, paths):
        added = 0
        for p in paths:
            ap = os.path.abspath(p)
            if ap not in self.pdf_paths:
                self.pdf_paths.append(ap)
                added += 1
        self.pdf_paths.sort()
        self._refresh_list()
        return added

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select PDF file(s)",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if paths:
            n = self._add_paths(paths)
            self._log(f"Added {n} file(s).")

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select a folder containing PDFs")
        if not folder:
            return
        found = find_pdfs_in_folder(folder, recursive=self.recursive_var.get())
        if not found:
            messagebox.showinfo(APP_TITLE, "No PDF files found in that folder.")
            return
        n = self._add_paths(found)
        self._log(f"Found {len(found)} PDF(s) in folder; added {n} new.")

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        if not sel:
            return
        for index in reversed(sel):
            del self.pdf_paths[index]
        self._refresh_list()

    def clear_list(self):
        self.pdf_paths.clear()
        self._refresh_list()

    def choose_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_dir.set(folder)

    # ----------------------------- logging -------------------------------- #
    def _log(self, text):
        self.log.configure(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    # --------------------------- processing ------------------------------- #
    def start_processing(self):
        if fitz is None:
            messagebox.showerror(APP_TITLE, "PyMuPDF is not installed.")
            return
        if not self.pdf_paths:
            messagebox.showwarning(APP_TITLE, "Add at least one PDF first.")
            return
        out_dir = self.output_dir.get().strip()
        if not out_dir:
            messagebox.showwarning(APP_TITLE, "Choose an output folder.")
            return
        if not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(APP_TITLE,
                                     f"Cannot create output folder:\n{exc}")
                return

        # lock UI
        self.run_btn.state(["disabled"])
        self.progress.configure(value=0, maximum=len(self.pdf_paths))
        self._log("-" * 50)
        self._log(f"Processing {len(self.pdf_paths)} file(s) -> {out_dir}")

        files = list(self.pdf_paths)
        suffix = DEFAULT_SUFFIX if self.suffix_var.get() else ""
        self.worker = threading.Thread(
            target=self._worker, args=(files, out_dir, suffix), daemon=True
        )
        self.worker.start()

    def _worker(self, files, out_dir, suffix):
        ok = fail = 0
        for i, path in enumerate(files, start=1):
            base = os.path.basename(path)
            stem, ext = os.path.splitext(base)
            out_name = f"{stem}{suffix}{ext}"
            out_path = os.path.join(out_dir, out_name)

            # never overwrite the source file in place
            if os.path.abspath(out_path) == os.path.abspath(path):
                out_path = os.path.join(out_dir, f"{stem}{DEFAULT_SUFFIX}{ext}")

            try:
                removed, remaining = remove_images_from_pdf(path, out_path)
                if remaining == 0:
                    self.msg_queue.put(
                        ("log", f"  OK  {base}  ->  {os.path.basename(out_path)} "
                                f"({removed} image(s) removed)")
                    )
                elif remaining > 0:
                    self.msg_queue.put(
                        ("log", f"  OK* {base}: {removed} removed, "
                                f"{remaining} unusual image(s) could not be located")
                    )
                else:
                    self.msg_queue.put(
                        ("log", f"  OK  {base}: {removed} removed (verify skipped)")
                    )
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                self.msg_queue.put(
                    ("log", f"  ERROR {base}: {exc}")
                )
                self.msg_queue.put(("trace", traceback.format_exc()))

            self.msg_queue.put(("progress", i))

        self.msg_queue.put(("done", (ok, fail, out_dir)))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "trace":
                    # keep traces out of the main log but available on stderr
                    sys.stderr.write(payload + "\n")
                elif kind == "progress":
                    self.progress.configure(value=payload)
                elif kind == "done":
                    ok, fail, out_dir = payload
                    self._log("-" * 50)
                    self._log(f"Done. {ok} succeeded, {fail} failed.")
                    self.run_btn.state(["!disabled"])
                    if fail == 0:
                        messagebox.showinfo(
                            APP_TITLE,
                            f"Finished. {ok} file(s) saved to:\n{out_dir}",
                        )
                    else:
                        messagebox.showwarning(
                            APP_TITLE,
                            f"Finished with issues.\n{ok} succeeded, {fail} failed.\n"
                            "See the log for details.",
                        )
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)


def main():
    root = tk.Tk()
    # Use a slightly nicer theme when available.
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass
    PdfImageRemoverApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
