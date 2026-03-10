# Batch Image Tool (Windows)

A simple Windows desktop tool for batch image editing: resize, convert format, rotate, flip, and grayscale.

## Requirements

- **Python 3.10+** (install from [python.org](https://www.python.org/downloads/))
- **Pillow** and **Flask** (installed via requirements.txt)

## Setup (one time)

**Easiest:** Double-click **`setup.bat`** in the project folder. It creates a virtual environment and installs dependencies. Do this once (or after pulling updates).

**Manual:** Open a terminal in the project folder, then:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run the app

You can run either the **web UI** or the **desktop (tkinter) UI**; choose the one you want.

| Launcher | What it does |
|----------|----------------|
| **`Launch.bat`** or **`Launch-web.bat`** | Starts the **web UI** (browser at http://127.0.0.1:5000). No tkinter needed. |
| **`Launch-tk.bat`** | Starts the **desktop (tkinter) window**. Requires tkinter. |

**From terminal (with venv activated):**
- Web: `python run.py` or `python run.py --web` or `python -m app_web`
- Desktop: `python run.py --tk` or `python -m gui`

## Features

- **Input** – Either choose an **input folder** or paste a **list of file paths** (one per line). List mode accepts paths with quotes and trailing punctuation (e.g. from export tools); the app strips them and uses paths that exist and have an image extension.
- **Output** – Choose **Single folder** (one path; empty = `batch_output` inside the input folder in folder mode) or **Same folder as each source** (each file is written next to its input). For either mode you can optionally enable **Use single output filename**: every image is saved with the same base name (extension added automatically); if multiple files end up in the same folder, suffixes _1, _2, … are added. Conflict handling is automatic (no prompts). When the output format differs from the input (e.g. padded PNG from a JPG), the extension change avoids conflicts.
- **Resize**
  - **Exact size** – Set width × height in pixels (e.g. 800 × 600).
  - **Max width / max height** – Resize so the image fits within these limits while keeping aspect ratio (optional).
- **Pad to target size (transparent PNG)** – Pad the image with fully transparent pixels (alpha=0) to reach a target resolution without stretching/cropping. Includes alignment options (left/center/right × top/center/bottom). When enabled, output is forced to PNG.
  - **Target by pixels** – Set the exact output canvas size (W×H).
  - **Target by ratio (W:H)** – Provide a ratio like `1:1` or `3.14:7.2`. The tool will compute the smallest integer canvas (in pixels) that fits the image while matching that aspect ratio, then pad with transparency.
  - **Saved ratio presets** – Pick a named preset (e.g. **manga** = `0.708:1`) from the dropdown, or save the current ratio as a new preset for later. Presets are stored in `ratio_presets.json` in the project folder.
- **Output format** – Same as source, or convert to JPEG, PNG, WebP, or BMP.
- **JPEG quality** – 1–100 when saving as JPEG.
- **Rotate** – Rotate by 0–360 degrees.
- **Flip** – Flip horizontal and/or vertical.
- **Grayscale** – Convert all images to grayscale.

Supported input formats: JPG, JPEG, PNG, GIF, BMP, WebP, TIFF.

## Using from code

You can use the processor without the GUI:

```python
from processor import batch_process, get_image_paths, parse_file_list
from pathlib import Path

# Option A: process all images in a folder
success, failed, errors, notice = batch_process(
    input_folder="C:/path/to/images",
    output_folder="C:/path/to/output",
    max_width=1200,
    keep_aspect=True,
    output_format="jpeg",
    quality=85,
)

# Option B: process a list of file paths (e.g. pasted text)
paths = parse_file_list('''"E:\\Games\\Project\\img\\char.png"
C:/Other/file.png''')
success, failed, errors, notice = batch_process(
    output_folder="C:/path/to/output",
    input_files=paths,
    max_width=1200,
)
# Option C: save each file next to its source (suffix added if name exists)
success, failed, errors, notice = batch_process(
    input_files=paths,
    output_to_source=True,
    max_width=1200,
)
if notice:
    print(notice)
print(f"Done: {success} ok, {failed} failed")
```

## License

Use and modify as you like.
