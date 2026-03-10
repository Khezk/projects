"""
Tkinter desktop GUI for batch image editing.
Run directly: python -m gui (requires tkinter).
Use python -m app_web or run.py --web for the web UI instead.
"""
import os
from pathlib import Path
import threading

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    HAS_TK = True
except ImportError:
    HAS_TK = False

from processor import batch_process, get_image_paths, parse_file_list
from presets import load_presets


def run_tk():
    root = tk.Tk()
    root.title("Batch Image Tool")
    root.minsize(520, 520)
    root.geometry("580x820")

    # Scrollable container so all controls (including file-list mode) are reachable
    canvas = tk.Canvas(root, highlightthickness=0)
    vbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=canvas.yview)
    main = ttk.Frame(canvas, padding=12)

    main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=main, anchor=tk.NW)
    canvas.configure(yscrollcommand=vbar.set)

    def _on_canvas_configure(_):
        canvas.itemconfig(canvas.find_all()[0], width=canvas.winfo_width())
    canvas.bind("<Configure>", _on_canvas_configure)

    vbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Variables
    input_mode = tk.StringVar(value="folder")
    input_folder = tk.StringVar()
    output_mode = tk.StringVar(value="single")
    output_folder = tk.StringVar()
    output_stem = tk.StringVar()
    resize_w = tk.StringVar(value="")
    resize_h = tk.StringVar(value="")
    max_w = tk.StringVar(value="")
    max_h = tk.StringVar(value="")
    keep_aspect = tk.BooleanVar(value=True)
    pad_w = tk.StringVar(value="")
    pad_h = tk.StringVar(value="")
    pad_ratio = tk.StringVar(value="")
    pad_align_x = tk.StringVar(value="center")
    pad_align_y = tk.StringVar(value="center")
    output_format = tk.StringVar(value="Same as source")
    quality = tk.IntVar(value=85)
    rotate = tk.StringVar(value="0")
    flip_h = tk.BooleanVar(value=False)
    flip_v = tk.BooleanVar(value=False)
    grayscale = tk.BooleanVar(value=False)

    # --- Input mode ---
    ttk.Label(main, text="Input:").grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
    mode_f = ttk.Frame(main)
    mode_f.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
    ttk.Radiobutton(mode_f, text="Folder", variable=input_mode, value="folder").pack(side=tk.LEFT, padx=(0, 12))
    ttk.Radiobutton(mode_f, text="List of file paths", variable=input_mode, value="file_list").pack(side=tk.LEFT)

    folder_f = ttk.Frame(main)
    folder_f.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(0, 2))
    root.columnconfigure(0, weight=1)
    main.columnconfigure(0, weight=1)
    ttk.Label(folder_f, text="Input folder").pack(anchor=tk.W)
    row1 = ttk.Frame(folder_f)
    row1.pack(fill=tk.X, pady=(2, 0))
    ttk.Entry(row1, textvariable=input_folder, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
    ttk.Button(row1, text="Browse…", command=lambda: input_folder.set(filedialog.askdirectory() or input_folder.get())).pack(side=tk.RIGHT)

    list_f = ttk.Frame(main)
    list_f.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 2))
    ttk.Label(list_f, text="File paths (one per line)").pack(anchor=tk.W)
    file_list_text = scrolledtext.ScrolledText(list_f, height=6, width=58, wrap=tk.WORD)
    file_list_text.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
    list_f.grid_remove()

    def _toggle_input():
        if input_mode.get() == "file_list":
            folder_f.grid_remove()
            list_f.grid()
        else:
            list_f.grid_remove()
            folder_f.grid()

    input_mode.trace_add("write", lambda *a: _toggle_input())
    _toggle_input()

    ttk.Label(main, text="Output:").grid(row=4, column=0, sticky=tk.W, pady=(12, 4))
    out_mode_f = ttk.Frame(main)
    out_mode_f.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
    ttk.Radiobutton(out_mode_f, text="Single folder", variable=output_mode, value="single").pack(side=tk.LEFT, padx=(0, 12))
    ttk.Radiobutton(out_mode_f, text="Single output filename", variable=output_mode, value="single_stem").pack(side=tk.LEFT, padx=(0, 12))
    ttk.Radiobutton(out_mode_f, text="Same as each source", variable=output_mode, value="same_as_source").pack(side=tk.LEFT)
    row2 = ttk.Frame(main)
    row2.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=(0, 4))
    ttk.Label(row2, text="Output folder").pack(anchor=tk.W)
    out_row = ttk.Frame(row2)
    out_row.pack(fill=tk.X, pady=(2, 0))
    ttk.Entry(out_row, textvariable=output_folder, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
    ttk.Button(out_row, text="Browse…", command=lambda: output_folder.set(filedialog.askdirectory() or output_folder.get())).pack(side=tk.RIGHT)
    out_stem_f = ttk.Frame(main)
    out_stem_f.grid(row=7, column=0, columnspan=2, sticky=tk.EW, pady=(0, 12))
    ttk.Label(out_stem_f, text="Output filename (no extension; for “Single output filename” only)").pack(anchor=tk.W)
    ttk.Entry(out_stem_f, textvariable=output_stem, width=40).pack(fill=tk.X, pady=(2, 0))

    # --- Resize ---
    ttk.Separator(main, orient=tk.HORIZONTAL).grid(row=8, column=0, columnspan=2, sticky=tk.EW, pady=8)
    ttk.Label(main, text="Resize (optional):").grid(row=9, column=0, sticky=tk.W, pady=(0, 4))
    resize_f = ttk.Frame(main)
    resize_f.grid(row=10, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))
    ttk.Entry(resize_f, textvariable=resize_w, width=6).pack(side=tk.LEFT)
    ttk.Label(resize_f, text="×").pack(side=tk.LEFT, padx=2)
    ttk.Entry(resize_f, textvariable=resize_h, width=6).pack(side=tk.LEFT)
    ttk.Label(resize_f, text="px (exact size). Or max width/height below (keep aspect):").pack(side=tk.LEFT, padx=(8, 0))

    max_f = ttk.Frame(main)
    max_f.grid(row=11, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))
    ttk.Entry(max_f, textvariable=max_w, width=6).pack(side=tk.LEFT)
    ttk.Label(max_f, text="max width").pack(side=tk.LEFT, padx=(0, 8))
    ttk.Entry(max_f, textvariable=max_h, width=6).pack(side=tk.LEFT, padx=(8, 0))
    ttk.Label(max_f, text="max height (px)").pack(side=tk.LEFT, padx=(0, 8))
    ttk.Checkbutton(main, text="Keep aspect ratio for max size", variable=keep_aspect).grid(row=12, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))

    # --- Pad ---
    ttk.Label(main, text="Pad to target size (transparent PNG, optional):").grid(row=13, column=0, sticky=tk.W, pady=(0, 4))
    pad_f = ttk.Frame(main)
    pad_f.grid(row=14, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
    ttk.Entry(pad_f, textvariable=pad_w, width=6).pack(side=tk.LEFT)
    ttk.Label(pad_f, text="×").pack(side=tk.LEFT, padx=2)
    ttk.Entry(pad_f, textvariable=pad_h, width=6).pack(side=tk.LEFT)
    ttk.Label(pad_f, text="px").pack(side=tk.LEFT, padx=(6, 0))

    pad_ratio_f = ttk.Frame(main)
    pad_ratio_f.grid(row=15, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
    ttk.Label(pad_ratio_f, text="Preset").pack(side=tk.LEFT)
    _base_dir = Path(__file__).resolve().parent
    _presets = load_presets(_base_dir)
    _preset_names = ["", *sorted(_presets.keys(), key=str.lower)]
    preset_combo = ttk.Combobox(pad_ratio_f, width=10, state="readonly", values=_preset_names)
    preset_combo.pack(side=tk.LEFT, padx=(4, 8))

    def _on_preset_change(_event=None):
        name = preset_combo.get()
        if name and name in _presets:
            pad_ratio.set(_presets[name])

    preset_combo.bind("<<ComboboxSelected>>", _on_preset_change)
    ttk.Label(pad_ratio_f, text="Or ratio W:H").pack(side=tk.LEFT, padx=(8, 0))
    ttk.Entry(pad_ratio_f, textvariable=pad_ratio, width=16).pack(side=tk.LEFT, padx=(4, 0))

    pad_align_f = ttk.Frame(main)
    pad_align_f.grid(row=15, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))
    ttk.Label(pad_align_f, text="Align X:").pack(side=tk.LEFT)
    ttk.Combobox(pad_align_f, textvariable=pad_align_x, width=8, state="readonly", values=("left", "center", "right")).pack(side=tk.LEFT, padx=(4, 12))
    ttk.Label(pad_align_f, text="Align Y:").pack(side=tk.LEFT)
    ttk.Combobox(pad_align_f, textvariable=pad_align_y, width=8, state="readonly", values=("top", "center", "bottom")).pack(side=tk.LEFT, padx=(4, 0))

    # --- Format & quality ---
    ttk.Separator(main, orient=tk.HORIZONTAL).grid(row=16, column=0, columnspan=2, sticky=tk.EW, pady=(12, 8))
    ttk.Label(main, text="Output format:").grid(row=17, column=0, sticky=tk.W, pady=(0, 2))
    fmt_combo = ttk.Combobox(main, textvariable=output_format, width=18, state="readonly",
                             values=("Same as source", "jpeg", "png", "webp", "bmp"))
    fmt_combo.grid(row=18, column=0, sticky=tk.W, pady=(0, 4))
    ttk.Label(main, text="JPEG quality (1–100):").grid(row=19, column=0, sticky=tk.W, pady=(0, 2))
    ttk.Spinbox(main, textvariable=quality, from_=1, to=100, width=6).grid(row=20, column=0, sticky=tk.W, pady=(0, 8))

    # --- Transform ---
    ttk.Label(main, text="Rotate (degrees):").grid(row=21, column=0, sticky=tk.W, pady=(0, 2))
    ttk.Spinbox(main, textvariable=rotate, from_=0, to=360, width=6).grid(row=22, column=0, sticky=tk.W, pady=(0, 4))
    ttk.Checkbutton(main, text="Flip horizontal", variable=flip_h).grid(row=23, column=0, sticky=tk.W, pady=2)
    ttk.Checkbutton(main, text="Flip vertical", variable=flip_v).grid(row=24, column=0, sticky=tk.W, pady=2)
    ttk.Checkbutton(main, text="Convert to grayscale", variable=grayscale).grid(row=25, column=0, sticky=tk.W, pady=(2, 8))

    # --- Log & Run ---
    ttk.Separator(main, orient=tk.HORIZONTAL).grid(row=27, column=0, columnspan=2, sticky=tk.EW, pady=(12, 8))
    ttk.Label(main, text="Log:").grid(row=28, column=0, sticky=tk.W, pady=(0, 2))
    log = scrolledtext.ScrolledText(main, height=6, width=58, state=tk.DISABLED, wrap=tk.WORD)
    log.grid(row=29, column=0, columnspan=2, sticky=tk.NSEW, pady=(0, 8))
    main.rowconfigure(29, weight=1)

    def _on_mousewheel(event):
        w = event.widget
        if w == file_list_text or w == log:
            return
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    root.bind_all("<MouseWheel>", _on_mousewheel)

    def log_msg(msg: str):
        log.config(state=tk.NORMAL)
        log.insert(tk.END, msg + "\n")
        log.see(tk.END)
        log.config(state=tk.DISABLED)

    def run_batch():
        mode = input_mode.get()
        out_mode = output_mode.get()
        output_to_source = out_mode == "same_as_source"
        out = output_folder.get().strip()
        paths = None
        inp = None
        stem_override = (output_stem.get() or "").strip() or None
        if out_mode == "single_stem" and (not out or not stem_override):
            messagebox.showerror("Error", "Output folder and output filename are required for “Single output filename”.")
            return
        if mode == "file_list":
            text = file_list_text.get("1.0", tk.END).strip()
            if not text:
                messagebox.showerror("Error", "Paste at least one file path in the list.")
                return
            paths = parse_file_list(text)
            if not paths:
                messagebox.showerror("Error", "No valid image paths found. Check that paths exist and have an image extension.")
                return
            if not output_to_source and out_mode != "single_stem" and not out:
                messagebox.showerror("Error", "Output folder is required when using a single output folder.")
                return
        else:
            inp = input_folder.get().strip()
            if not inp or not Path(inp).is_dir():
                messagebox.showerror("Error", "Please select a valid input folder.")
                return
            if not output_to_source and out_mode != "single_stem" and not out:
                out = os.path.join(inp, "batch_output")
        if not output_to_source:
            os.makedirs(out, exist_ok=True)

        def parse_int(s, default=None):
            s = (s or "").strip()
            if not s:
                return default
            try:
                return int(s)
            except ValueError:
                return default

        rw = parse_int(resize_w.get())
        rh = parse_int(resize_h.get())
        resize_tuple = (rw, rh) if (rw is not None and rh is not None and rw > 0 and rh > 0) else None
        mw = parse_int(max_w.get())
        mh = parse_int(max_h.get())
        rot = parse_int(rotate.get(), 0) % 360
        pw = parse_int(pad_w.get())
        ph = parse_int(pad_h.get())
        pad_to = (pw, ph) if (pw is not None and ph is not None and pw > 0 and ph > 0) else None
        ratio_str = (pad_ratio.get() or "").strip()
        pad_ratio_tuple = None
        if pad_to is None and ratio_str:
            if ":" in ratio_str:
                a, b = ratio_str.split(":", 1)
                try:
                    rw = float(a.strip())
                    rh = float(b.strip())
                    if rw > 0 and rh > 0:
                        pad_ratio_tuple = (rw, rh)
                except ValueError:
                    pad_ratio_tuple = None
        align_x = (pad_align_x.get() or "center").strip().lower()
        align_y = (pad_align_y.get() or "center").strip().lower()
        fmt = None if output_format.get() == "Same as source" else output_format.get().strip().lower()
        if fmt == "jpeg":
            fmt = "jpeg"
        if pad_to or pad_ratio_tuple:
            fmt = "png"

        if not output_to_source:
            log_msg(f"Output: {out}")
        log_msg("Processing…")

        def do_work():
            try:
                if paths is not None:
                    success, fail, errs, notice = batch_process(
                        output_folder=out if not output_to_source else None,
                        input_files=paths,
                        output_to_source=output_to_source,
                        output_stem=stem_override if out_mode == "single_stem" else None,
                        resize=resize_tuple,
                        max_width=mw,
                        max_height=mh,
                        keep_aspect=keep_aspect.get(),
                        pad_to=pad_to,
                        pad_ratio=pad_ratio_tuple,
                        pad_align_x=align_x,
                        pad_align_y=align_y,
                        output_format=fmt,
                        quality=quality.get(),
                        rotate_deg=rot,
                        flip_horizontal=flip_h.get(),
                        flip_vertical=flip_v.get(),
                        grayscale=grayscale.get(),
                        progress_callback=lambda c, t: None,
                    )
                else:
                    success, fail, errs, notice = batch_process(
                        inp,
                        out if not output_to_source else None,
                        output_to_source=output_to_source,
                        output_stem=stem_override if out_mode == "single_stem" else None,
                        resize=resize_tuple,
                    max_width=mw,
                    max_height=mh,
                    keep_aspect=keep_aspect.get(),
                    pad_to=pad_to,
                    pad_ratio=pad_ratio_tuple,
                    pad_align_x=align_x,
                    pad_align_y=align_y,
                    output_format=fmt,
                    quality=quality.get(),
                    rotate_deg=rot,
                    flip_horizontal=flip_h.get(),
                    flip_vertical=flip_v.get(),
                    grayscale=grayscale.get(),
                    progress_callback=lambda c, t: None,
                    )
                root.after(0, lambda: done(success, fail, errs, notice))
            except Exception as e:
                root.after(0, lambda: log_msg(f"Error: {e}"))

        def done(success, fail, errs, notice):
            log_msg(f"Done. Success: {success}, Failed: {fail}")
            if notice:
                log_msg(notice)
            for e in errs[:10]:
                log_msg(f"  {e}")
            if len(errs) > 10:
                log_msg(f"  … and {len(errs) - 10} more.")
            messagebox.showinfo("Batch complete", f"Processed {success} images, {fail} failed.")

        threading.Thread(target=do_work, daemon=True).start()

    ttk.Button(main, text="Run batch", command=run_batch).grid(row=30, column=0, columnspan=2, pady=(8, 12))

    root.mainloop()


if __name__ == "__main__":
    if not HAS_TK:
        print("tkinter not found. Use the web UI instead: python -m app_web")
        print("Or: python run.py --web")
        raise SystemExit(1)
    run_tk()
