"""
Web-based UI for batch image editing (no tkinter required).
Run with: python -m app_web
Then open http://127.0.0.1:5000 in your browser.
"""
import os
import webbrowser
import threading
from pathlib import Path
from flask import Flask, request, render_template_string, redirect, url_for

from processor import batch_process, get_image_paths, parse_file_list
from presets import load_presets, load_presets_list, save_presets

_BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)

HTML = r"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Batch Image Tool</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; max-width: 560px; margin: 24px auto; padding: 0 16px; }
    h1 { font-size: 1.35rem; margin-bottom: 16px; }
    label { display: block; margin-top: 12px; font-weight: 500; }
    input[type="text"], input[type="number"], select { width: 100%; padding: 8px; margin-top: 4px; }
    .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    .row input[type="number"] { width: 80px; }
    .row label { margin-top: 0; }
    .inline { display: inline-block; margin-right: 16px; margin-top: 8px; }
    button { margin-top: 20px; padding: 10px 24px; font-size: 1rem; cursor: pointer; background: #0066cc; color: #fff; border: none; border-radius: 6px; }
    button:hover { background: #0052a3; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    #log { margin-top: 16px; padding: 12px; background: #f5f5f5; border-radius: 6px; white-space: pre-wrap; font-family: Consolas, monospace; font-size: 13px; min-height: 120px; max-height: 240px; overflow-y: auto; }
    .success { color: #0a6b0a; }
    .error { color: #b00; }
    .hint { font-size: 0.9rem; color: #666; margin-top: 4px; }
  </style>
</head>
<body>
  <h1>Batch Image Tool</h1>
  <form method="post" action="/run" id="form">
    <label>Input mode</label>
    <div class="row">
      <label class="inline"><input type="radio" name="input_mode" value="folder" {{ 'checked' if input_mode == 'folder' else '' }}> Folder</label>
      <label class="inline"><input type="radio" name="input_mode" value="file_list" {{ 'checked' if input_mode == 'file_list' else '' }}> List of file paths</label>
    </div>

    <div id="input_folder_section">
      <label>Input folder (full path)</label>
      <input type="text" name="input_folder" id="input_folder" placeholder="e.g. C:\Users\You\Pictures\photos" value="{{ input_folder or '' }}">
      <p class="hint">Enter the folder containing images to process.</p>
    </div>

    <div id="input_file_list_section" style="display: none;">
      <label>File paths (one per line; quotes and trailing punctuation are stripped)</label>
      <textarea name="input_file_list" id="input_file_list" rows="10" placeholder="Paste paths here, e.g.&#10;&quot;E:\Games\Project\img\char.png&quot;&#10;C:\Other\file.png" style="width: 100%; font-family: Consolas, monospace; font-size: 13px;">{{ input_file_list or '' }}</textarea>
      <p class="hint">Each line = one image path. Supports &quot;path&quot;, 'path', or plain path.</p>
    </div>

    <label>Output</label>
    <div class="row">
      <label class="inline"><input type="radio" name="output_mode" value="single" {{ 'checked' if output_mode == 'single' else '' }}> Single folder</label>
      <label class="inline"><input type="radio" name="output_mode" value="single_stem" {{ 'checked' if output_mode == 'single_stem' else '' }}> Single output filename</label>
      <label class="inline"><input type="radio" name="output_mode" value="same_as_source" {{ 'checked' if output_mode == 'same_as_source' else '' }}> Same folder as each source</label>
    </div>
    <div id="output_folder_section">
      <label>Output folder (full path)</label>
      <input type="text" name="output_folder" id="output_folder" placeholder="e.g. C:\Users\You\Pictures\output" value="{{ output_folder or '' }}">
      <p class="hint">Leave empty to use &quot;batch_output&quot; inside the input folder (folder mode only).</p>
    </div>
    <div id="output_stem_section" style="display: none;">
      <label>Output filename (without extension)</label>
      <input type="text" name="output_stem" id="output_stem" placeholder="e.g. result" value="{{ output_stem or '' }}">
      <p class="hint">Every image will use this name; extension is added automatically. If multiple files go to the same folder, a suffix (_1, _2, …) is added.</p>
    </div>
    <p class="hint" id="output_same_hint" style="display: none;">Each file is saved next to its source. If a name is already in use, a suffix (_1, _2, …) is added automatically.</p>

    <fieldset style="margin-top: 16px; padding: 12px; border-radius: 6px; border: 1px solid #ccc;">
      <legend>Resize (optional)</legend>
      <div class="row">
        <label>Width <input type="number" name="resize_w" min="0" placeholder="—" value="{{ resize_w or '' }}"></label>
        <span>×</span>
        <label>Height <input type="number" name="resize_h" min="0" placeholder="—" value="{{ resize_h or '' }}"></label>
        <span>px (exact)</span>
      </div>
      <div class="row" style="margin-top: 8px;">
        <label>Max width <input type="number" name="max_w" min="0" placeholder="—" value="{{ max_w or '' }}"></label>
        <label>Max height <input type="number" name="max_h" min="0" placeholder="—" value="{{ max_h or '' }}"></label>
        <label class="inline"><input type="checkbox" name="keep_aspect" {{ 'checked' if keep_aspect else '' }}> Keep aspect</label>
      </div>
    </fieldset>

    <fieldset style="margin-top: 16px; padding: 12px; border-radius: 6px; border: 1px solid #ccc;">
      <legend>Pad to target size (transparent PNG)</legend>
      <div class="row">
        <label>Target width <input type="number" name="pad_w" min="0" placeholder="—" value="{{ pad_w or '' }}"></label>
        <label>Target height <input type="number" name="pad_h" min="0" placeholder="—" value="{{ pad_h or '' }}"></label>
      </div>
      <div class="row" style="margin-top: 8px;">
        <label>Ratio preset
          <select id="ratio_preset" style="width: auto; min-width: 120px;">
            <option value="">Custom</option>
            {% for p in presets %}
            <option value="{{ p.ratio }}" {{ 'selected' if pad_ratio == p.ratio else '' }}>{{ p.name }}</option>
            {% endfor %}
          </select>
        </label>
        <label>Or target ratio (W:H)
          <input type="text" name="pad_ratio" id="pad_ratio_input" placeholder="e.g. 1:1 or 3.14:7.2" value="{{ pad_ratio or '' }}">
        </label>
      </div>
      <div class="row" style="margin-top: 6px; font-size: 0.9rem;">
        <label>Save current ratio as preset: <input type="text" id="save_preset_name" placeholder="Name" style="width: 80px;"> <button type="button" id="btn_save_preset">Save</button></label>
        <label>Delete preset: <select id="delete_preset_name" style="width: auto;">{% for p in presets %}<option value="{{ p.name }}">{{ p.name }}</option>{% endfor %}</select> <button type="button" id="btn_delete_preset">Delete</button></label>
      </div>
      <div class="row" style="margin-top: 8px;">
        <label>Horizontal align
          <select name="pad_align_x">
            <option value="left" {{ 'selected' if pad_align_x == 'left' else '' }}>Left</option>
            <option value="center" {{ 'selected' if pad_align_x == 'center' else '' }}>Center</option>
            <option value="right" {{ 'selected' if pad_align_x == 'right' else '' }}>Right</option>
          </select>
        </label>
        <label>Vertical align
          <select name="pad_align_y">
            <option value="top" {{ 'selected' if pad_align_y == 'top' else '' }}>Top</option>
            <option value="center" {{ 'selected' if pad_align_y == 'center' else '' }}>Center</option>
            <option value="bottom" {{ 'selected' if pad_align_y == 'bottom' else '' }}>Bottom</option>
          </select>
        </label>
      </div>
      <p class="hint">If you set both target width+height and ratio, width+height wins. Output is forced to PNG.</p>
    </fieldset>

    <label>Output format</label>
    <select name="output_format">
      <option value="same" {{ 'selected' if output_format == 'same' else '' }}>Same as source</option>
      <option value="jpeg" {{ 'selected' if output_format == 'jpeg' else '' }}>JPEG</option>
      <option value="png" {{ 'selected' if output_format == 'png' else '' }}>PNG</option>
      <option value="webp" {{ 'selected' if output_format == 'webp' else '' }}>WebP</option>
      <option value="bmp" {{ 'selected' if output_format == 'bmp' else '' }}>BMP</option>
    </select>

    <label>JPEG quality (1–100)</label>
    <input type="number" name="quality" min="1" max="100" value="{{ quality or 85 }}">

    <label>Rotate (degrees)</label>
    <input type="number" name="rotate" min="0" max="360" value="{{ rotate or 0 }}">

    <div style="margin-top: 12px;">
      <label class="inline"><input type="checkbox" name="flip_h" {{ 'checked' if flip_h else '' }}> Flip horizontal</label>
      <label class="inline"><input type="checkbox" name="flip_v" {{ 'checked' if flip_v else '' }}> Flip vertical</label>
      <label class="inline"><input type="checkbox" name="grayscale" {{ 'checked' if grayscale else '' }}> Grayscale</label>
    </div>

    <button type="submit" id="btn">Run batch</button>
  </form>

  <div id="log">{{ log or 'Log will appear here after you run.' }}</div>

  <script>
    function toggleInputMode() {
      var mode = document.querySelector('input[name="input_mode"]:checked');
      var folderSection = document.getElementById('input_folder_section');
      var listSection = document.getElementById('input_file_list_section');
      if (mode && mode.value === 'file_list') {
        folderSection.style.display = 'none';
        listSection.style.display = 'block';
        document.getElementById('input_folder').removeAttribute('required');
      } else {
        folderSection.style.display = 'block';
        listSection.style.display = 'none';
        listSection.querySelector('textarea').removeAttribute('required');
        document.getElementById('input_folder').setAttribute('required', 'required');
      }
    }
    function toggleOutputMode() {
      var mode = document.querySelector('input[name="output_mode"]:checked');
      var folderSection = document.getElementById('output_folder_section');
      var stemSection = document.getElementById('output_stem_section');
      var sameHint = document.getElementById('output_same_hint');
      if (mode && mode.value === 'same_as_source') {
        folderSection.style.display = 'none';
        stemSection.style.display = 'none';
        sameHint.style.display = 'block';
        document.getElementById('output_folder').removeAttribute('required');
      } else if (mode && mode.value === 'single_stem') {
        folderSection.style.display = 'block';
        stemSection.style.display = 'block';
        sameHint.style.display = 'none';
        document.getElementById('output_folder').setAttribute('required', 'required');
      } else {
        folderSection.style.display = 'block';
        stemSection.style.display = 'none';
        sameHint.style.display = 'none';
        document.getElementById('output_folder').removeAttribute('required');
      }
    }
    var inputRadios = document.querySelectorAll('input[name="input_mode"]');
    for (var i = 0; i < inputRadios.length; i++) inputRadios[i].addEventListener('change', toggleInputMode);
    toggleInputMode();
    var outputRadios = document.querySelectorAll('input[name="output_mode"]');
    for (var j = 0; j < outputRadios.length; j++) outputRadios[j].addEventListener('change', toggleOutputMode);
    toggleOutputMode();

    document.getElementById('form').onsubmit = function() {
      document.getElementById('btn').disabled = true;
      document.getElementById('log').textContent = 'Processing…';
    };
    var ratioPreset = document.getElementById('ratio_preset');
    var padRatioInput = document.getElementById('pad_ratio_input');
    if (ratioPreset && padRatioInput) {
      ratioPreset.addEventListener('change', function() {
        padRatioInput.value = this.value || '';
      });
      padRatioInput.addEventListener('input', function() {
        ratioPreset.value = '';
      });
    }
    var btnSave = document.getElementById('btn_save_preset');
    if (btnSave) {
      btnSave.addEventListener('click', function() {
        var name = document.getElementById('save_preset_name').value.trim();
        var ratio = document.getElementById('pad_ratio_input').value.trim();
        if (!name || !ratio || ratio.indexOf(':') === -1) { alert('Enter a name and a valid ratio (e.g. 0.708:1)'); return; }
        var form = document.createElement('form');
        form.method = 'post';
        form.action = '/save_preset';
        var n = document.createElement('input'); n.name = 'preset_name'; n.value = name; form.appendChild(n);
        var r = document.createElement('input'); r.name = 'preset_ratio'; r.value = ratio; form.appendChild(r);
        document.body.appendChild(form);
        form.submit();
      });
    }
    var btnDel = document.getElementById('btn_delete_preset');
    if (btnDel) {
      btnDel.addEventListener('click', function() {
        var name = document.getElementById('delete_preset_name').value;
        if (!name) return;
        if (!confirm('Delete preset "' + name + '"?')) return;
        var form = document.createElement('form');
        form.method = 'post';
        form.action = '/delete_preset';
        var n = document.createElement('input'); n.name = 'preset_name'; n.value = name; form.appendChild(n);
        document.body.appendChild(form);
        form.submit();
      });
    }
  </script>
</body>
</html>
"""


def parse_int(s, default=None):
    if s is None or (isinstance(s, str) and not s.strip()):
        return default
    try:
        return int(s)
    except (ValueError, TypeError):
        return default


def _template_context(**kwargs) -> dict:
    base = {
        "presets": load_presets_list(_BASE_DIR),
        "input_mode": "folder",
        "input_folder": None,
        "input_file_list": None,
        "output_mode": "single",
        "output_folder": None,
        "output_stem": None,
        "resize_w": None,
        "resize_h": None,
        "max_w": None,
        "max_h": None,
        "keep_aspect": True,
        "pad_w": None,
        "pad_h": None,
        "pad_ratio": None,
        "pad_align_x": "center",
        "pad_align_y": "center",
        "output_format": "same",
        "quality": "85",
        "rotate": "0",
        "flip_h": False,
        "flip_v": False,
        "grayscale": False,
        "log": None,
    }
    base.update(kwargs)
    return base


def parse_ratio(s: str | None) -> tuple[float, float] | None:
    """
    Parse ratio string like '1:2' or '3.14:7.2' into (w_ratio, h_ratio).
    Returns None if empty/invalid.
    """
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    if ":" not in s:
        return None
    a, b = s.split(":", 1)
    try:
        rw = float(a.strip())
        rh = float(b.strip())
    except ValueError:
        return None
    if rw <= 0 or rh <= 0:
        return None
    return (rw, rh)


@app.route("/")
def index():
    return render_template_string(
        HTML,
        **_template_context(
            input_mode=request.args.get("input_mode", "folder"),
            input_folder=request.args.get("input_folder"),
            input_file_list=request.args.get("input_file_list"),
            output_mode=request.args.get("output_mode", "single"),
            output_folder=request.args.get("output_folder"),
            output_stem=request.args.get("output_stem"),
            resize_w=request.args.get("resize_w"),
            resize_h=request.args.get("resize_h"),
            max_w=request.args.get("max_w"),
            max_h=request.args.get("max_h"),
            keep_aspect=request.args.get("keep_aspect") == "on",
            pad_w=request.args.get("pad_w"),
            pad_h=request.args.get("pad_h"),
            pad_ratio=request.args.get("pad_ratio"),
            pad_align_x=request.args.get("pad_align_x", "center"),
            pad_align_y=request.args.get("pad_align_y", "center"),
            output_format=request.args.get("output_format", "same"),
            quality=request.args.get("quality", "85"),
            rotate=request.args.get("rotate", "0"),
            flip_h=request.args.get("flip_h") == "on",
            flip_v=request.args.get("flip_v") == "on",
            grayscale=request.args.get("grayscale") == "on",
        ),
    )


@app.route("/run", methods=["POST"])
def run():
    input_mode = (request.form.get("input_mode") or "folder").strip()
    inp = (request.form.get("input_folder") or "").strip()
    file_list_text = (request.form.get("input_file_list") or "").strip()
    out = (request.form.get("output_folder") or "").strip()

    output_mode = (request.form.get("output_mode") or "single").strip()
    output_to_source = output_mode == "same_as_source"
    output_stem_raw = (request.form.get("output_stem") or "").strip()
    output_stem = output_stem_raw if output_mode == "single_stem" else None

    def _ctx(**kw):
        return _template_context(
            input_mode=input_mode,
            input_folder=inp or request.form.get("input_folder"),
            input_file_list=file_list_text or request.form.get("input_file_list"),
            output_mode=output_mode,
            output_folder=out or request.form.get("output_folder"),
            output_stem=output_stem_raw or request.form.get("output_stem"),
            **kw,
        )

    if input_mode == "file_list":
        if not file_list_text:
            return render_template_string(HTML, **_ctx(log="Error: Paste at least one file path in the list."))
        paths = parse_file_list(file_list_text)
        if not paths:
            return render_template_string(
                HTML,
                **_ctx(log="Error: No valid image paths found. Check that paths exist and have an image extension (.png, .jpg, etc.)."),
            )
        if output_mode == "single_stem" and (not out or not output_stem_raw):
            return render_template_string(HTML, **_ctx(log="Error: Output folder and output filename are required for “Single output filename”."))
        if not output_to_source and output_mode != "single_stem" and not out:
            return render_template_string(HTML, **_ctx(log="Error: Output folder is required when using a single output folder."))
        inp = None
    else:
        if not inp:
            return render_template_string(HTML, **_ctx(log="Error: Input folder is required."))
        if not Path(inp).is_dir():
            return render_template_string(HTML, **_ctx(log=f"Error: Not a valid folder: {inp}"))
        if output_mode == "single_stem" and (not out or not output_stem_raw):
            return render_template_string(HTML, **_ctx(log="Error: Output folder and output filename are required for “Single output filename”."))
        if not output_to_source and output_mode != "single_stem" and not out:
            out = os.path.join(inp, "batch_output")

    if not output_to_source:
        os.makedirs(out, exist_ok=True)

    rw = parse_int(request.form.get("resize_w"))
    rh = parse_int(request.form.get("resize_h"))
    resize = (rw, rh) if (rw is not None and rh is not None and rw > 0 and rh > 0) else None
    mw = parse_int(request.form.get("max_w"))
    mh = parse_int(request.form.get("max_h"))
    keep_aspect = request.form.get("keep_aspect") == "on"
    pad_w = parse_int(request.form.get("pad_w"))
    pad_h = parse_int(request.form.get("pad_h"))
    pad_to = (pad_w, pad_h) if (pad_w is not None and pad_h is not None and pad_w > 0 and pad_h > 0) else None
    pad_ratio_str = request.form.get("pad_ratio")
    pad_ratio = parse_ratio(pad_ratio_str) if pad_to is None else None
    pad_align_x = (request.form.get("pad_align_x") or "center").strip().lower()
    pad_align_y = (request.form.get("pad_align_y") or "center").strip().lower()
    fmt = request.form.get("output_format", "same").strip().lower()
    output_format = None if fmt == "same" else ("jpeg" if fmt == "jpeg" else fmt)
    quality = parse_int(request.form.get("quality"), 85)
    rotate = parse_int(request.form.get("rotate"), 0) % 360
    flip_h = request.form.get("flip_h") == "on"
    flip_v = request.form.get("flip_v") == "on"
    grayscale = request.form.get("grayscale") == "on"

    # Padding requires PNG output (alpha=0 pixels)
    if pad_to or pad_ratio:
        fmt = "png"
        output_format = "png"

    try:
        if input_mode == "file_list":
            success, failed, errors, notice = batch_process(
                output_folder=out if not output_to_source else None,
                input_files=paths,
                output_to_source=output_to_source,
                output_stem=output_stem,
                resize=resize,
                max_width=mw,
                max_height=mh,
                keep_aspect=keep_aspect,
                pad_to=pad_to,
                pad_ratio=pad_ratio,
                pad_align_x=pad_align_x,
                pad_align_y=pad_align_y,
                output_format=output_format,
                quality=quality,
                rotate_deg=rotate,
                flip_horizontal=flip_h,
                flip_vertical=flip_v,
                grayscale=grayscale,
            )
        else:
            success, failed, errors, notice = batch_process(
                input_folder=inp,
                output_folder=out if not output_to_source else None,
                output_to_source=output_to_source,
                output_stem=output_stem,
                resize=resize,
                max_width=mw,
                max_height=mh,
                keep_aspect=keep_aspect,
                pad_to=pad_to,
                pad_ratio=pad_ratio,
                pad_align_x=pad_align_x,
                pad_align_y=pad_align_y,
                output_format=output_format,
                quality=quality,
                rotate_deg=rotate,
                flip_horizontal=flip_h,
                flip_vertical=flip_v,
                grayscale=grayscale,
            )
        log_lines = [f"Done. Success: {success}, Failed: {failed}"]
        if not output_to_source:
            log_lines.insert(0, f"Output: {out}")
        if notice:
            log_lines.append(notice)
        for e in errors[:15]:
            log_lines.append(f"  {e}")
        if len(errors) > 15:
            log_lines.append(f"  … and {len(errors) - 15} more.")
        log = "\n".join(log_lines)
    except Exception as e:
        log = f"Error: {e}"

    return render_template_string(
        HTML,
        **_template_context(
            log=log,
            input_mode=input_mode,
            input_folder=inp,
            input_file_list=file_list_text,
            output_mode=output_mode,
            output_folder=out,
            output_stem=output_stem_raw,
            resize_w=request.form.get("resize_w"),
            resize_h=request.form.get("resize_h"),
            max_w=request.form.get("max_w"),
            max_h=request.form.get("max_h"),
            keep_aspect=keep_aspect,
            pad_w=request.form.get("pad_w"),
            pad_h=request.form.get("pad_h"),
            pad_ratio=pad_ratio_str,
            pad_align_x=pad_align_x,
            pad_align_y=pad_align_y,
            output_format=fmt,
            quality=request.form.get("quality", "85"),
            rotate=request.form.get("rotate", "0"),
            flip_h=flip_h,
            flip_v=flip_v,
            grayscale=grayscale,
        ),
    )


@app.route("/save_preset", methods=["POST"])
def save_preset():
    name = (request.form.get("preset_name") or "").strip()
    ratio = (request.form.get("preset_ratio") or "").strip()
    if not name:
        return redirect(url_for("index"))
    if parse_ratio(ratio) is None:
        return redirect(url_for("index"))
    presets = load_presets(_BASE_DIR)
    presets[name] = ratio
    save_presets(_BASE_DIR, presets)
    return redirect(url_for("index"))


@app.route("/delete_preset", methods=["POST"])
def delete_preset():
    name = (request.form.get("preset_name") or "").strip()
    if not name:
        return redirect(url_for("index"))
    presets = load_presets(_BASE_DIR)
    presets.pop(name, None)
    save_presets(_BASE_DIR, presets)
    return redirect(url_for("index"))


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
