"""
Batch image processor - resize, convert format, rotate, flip, and basic adjustments.
"""
import os
import math
from pathlib import Path
from PIL import Image

# Common image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}


def get_image_paths(folder: str) -> list[Path]:
    """Return list of image file paths in folder."""
    folder_path = Path(folder)
    if not folder_path.is_dir():
        return []
    return [
        p for p in folder_path.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]


def parse_file_list(text: str) -> list[Path]:
    """
    Parse a pasted list of file paths (e.g. one per line) with flexible formatting.
    - Strips whitespace; removes surrounding double/single quotes per line
    - Strips trailing commas and semicolons
    - Returns paths that exist, are files, and have a known image extension.
    """
    result: list[Path] = []
    seen: set[Path] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Remove one layer of surrounding quotes (tools often export "path" or 'path')
        if (line.startswith('"') and line.endswith('"')) or (line.startswith("'") and line.endswith("'")):
            line = line[1:-1].strip()
        # Trailing punctuation some tools add
        line = line.rstrip(",\t;")
        if not line:
            continue
        p = Path(line)
        if not p.is_file():
            continue
        if p.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        # Dedupe by resolved path
        try:
            key = p.resolve()
        except OSError:
            key = p
        if key not in seen:
            seen.add(key)
            result.append(p)
    return result


def _output_extension(input_path: Path, output_format: str | None) -> str:
    """Return the output file extension (e.g. .png) from format or input."""
    if output_format:
        if output_format.lower() in ("jpeg", "jpg"):
            return ".jpg"
        return f".{output_format.lower().lstrip('.')}"
    return input_path.suffix


def get_output_path(
    parent: Path,
    stem: str,
    ext: str,
    input_path: Path,
) -> tuple[Path, bool]:
    """
    Choose an output path that does not overwrite the source.
    Returns (path, used_suffix). used_suffix is True if we had to add _1, _2, etc.
    """
    try:
        input_resolved = input_path.resolve()
    except OSError:
        input_resolved = input_path
    desired = parent / f"{stem}{ext}"
    # Use desired only if it doesn't exist and is not the source (avoid overwriting)
    if not desired.exists():
        try:
            if desired.resolve() != input_resolved:
                return desired, False
        except OSError:
            return desired, False
    # Name in use or same as source: add _1, _2, ...
    for i in range(1, 10000):
        candidate = parent / f"{stem}_{i}{ext}"
        if not candidate.exists():
            try:
                if candidate.resolve() != input_resolved:
                    return candidate, True
            except OSError:
                return candidate, True
    return parent / f"{stem}_9999{ext}", True  # fallback


def get_next_path_for_stem(parent: Path, stem: str, ext: str) -> tuple[Path, bool]:
    """
    Return the next available path in parent with the given stem and extension.
    Uses stem.ext, then stem_1.ext, stem_2.ext, ... so multiple files can go to the same folder.
    Returns (path, used_suffix).
    """
    desired = parent / f"{stem}{ext}"
    if not desired.exists():
        return desired, False
    for i in range(1, 10000):
        candidate = parent / f"{stem}_{i}{ext}"
        if not candidate.exists():
            return candidate, True
    return parent / f"{stem}_9999{ext}", True  # fallback


def process_image(
    input_path: Path,
    output_dir: Path,
    *,
    output_path: Path | None = None,
    resize: tuple[int, int] | None = None,
    max_width: int | None = None,
    max_height: int | None = None,
    keep_aspect: bool = True,
    pad_to: tuple[int, int] | None = None,
    pad_ratio: tuple[float, float] | None = None,  # (w_ratio, h_ratio), e.g. (1.0, 2.0)
    pad_align_x: str = "center",  # left|center|right
    pad_align_y: str = "center",  # top|center|bottom
    output_format: str | None = None,
    quality: int = 85,
    rotate_deg: int = 0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    grayscale: bool = False,
) -> str | None:
    """
    Process a single image and save to output_dir.
    Returns error message or None on success.
    """
    try:
        with Image.open(input_path) as img:
            # Use RGB for JPEG output when image has alpha or palette
            if output_format == "jpeg" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            w, h = img.size

            # Resize
            if resize:
                new_w, new_h = resize
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            elif max_width or max_height:
                if keep_aspect:
                    ratio = 1.0
                    if max_width and w > max_width:
                        ratio = min(ratio, max_width / w)
                    if max_height and h > max_height:
                        ratio = min(ratio, max_height / h)
                    new_w = int(w * ratio)
                    new_h = int(h * ratio)
                    if (new_w, new_h) != (w, h):
                        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                else:
                    new_w = max_width or w
                    new_h = max_height or h
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            if rotate_deg:
                img = img.rotate(-rotate_deg, expand=True)
            if flip_horizontal:
                img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if flip_vertical:
                img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            if grayscale:
                img = img.convert("L")

            if (pad_to is not None) or (pad_ratio is not None):
                # If pad_ratio is provided (and pad_to is not), compute the smallest integer canvas
                # that contains the image and matches the desired aspect ratio.
                if pad_to is None and pad_ratio is not None:
                    rw, rh = pad_ratio
                    if rw <= 0 or rh <= 0:
                        return "Pad ratio numbers must be positive."
                    r = rw / rh
                    if not math.isfinite(r) or r <= 0:
                        return "Pad ratio must be a positive finite number."

                    cur_w, cur_h = img.size

                    # Candidate A: choose width based on height (then adjust height to match ratio)
                    w_a = max(cur_w, int(math.ceil(cur_h * r)))
                    h_a = int(math.ceil(w_a / r))

                    # Candidate B: choose height based on width (then adjust width to match ratio)
                    h_b = max(cur_h, int(math.ceil(cur_w / r)))
                    w_b = int(math.ceil(h_b * r))

                    # Pick the candidate that adds the fewest pixels (area), then perimeter as tie-breaker
                    area_a = w_a * h_a
                    area_b = w_b * h_b
                    if (area_b < area_a) or (area_b == area_a and (w_b + h_b) < (w_a + h_a)):
                        pad_to = (w_b, h_b)
                    else:
                        pad_to = (w_a, h_a)

                target_w, target_h = pad_to
                if target_w <= 0 or target_h <= 0:
                    return "Pad target width/height must be positive."
                cur_w, cur_h = img.size
                if target_w < cur_w or target_h < cur_h:
                    return f"Pad target {target_w}x{target_h} is smaller than image {cur_w}x{cur_h}."

                align_x = (pad_align_x or "center").strip().lower()
                align_y = (pad_align_y or "center").strip().lower()
                if align_x not in ("left", "center", "right"):
                    align_x = "center"
                if align_y not in ("top", "center", "bottom"):
                    align_y = "center"

                dx = target_w - cur_w
                dy = target_h - cur_h
                if align_x == "left":
                    off_x = 0
                elif align_x == "right":
                    off_x = dx
                else:
                    off_x = dx // 2

                if align_y == "top":
                    off_y = 0
                elif align_y == "bottom":
                    off_y = dy
                else:
                    off_y = dy // 2

                base = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
                img_rgba = img.convert("RGBA")
                base.alpha_composite(img_rgba, (off_x, off_y))
                img = base

                # Padding requires alpha=0 pixels, so output must be PNG
                output_format = "png"

            # Output path
            stem = input_path.stem
            ext = _output_extension(input_path, output_format)
            if output_path is not None:
                out_path = output_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                out_path = output_dir / f"{stem}{ext}"

            save_kw = {}
            if output_format in ("jpeg", "jpg") or ext.lower() in (".jpg", ".jpeg"):
                save_kw["quality"] = quality
                if img.mode == "RGBA":
                    img = img.convert("RGB")

            img.save(out_path, **save_kw)
            return None
    except Exception as e:
        return str(e)


def batch_process(
    input_folder: str | None = None,
    output_folder: str | None = None,
    input_files: list[Path] | None = None,
    *,
    output_to_source: bool = False,
    output_stem: str | None = None,
    resize: tuple[int, int] | None = None,
    max_width: int | None = None,
    max_height: int | None = None,
    keep_aspect: bool = True,
    pad_to: tuple[int, int] | None = None,
    pad_ratio: tuple[float, float] | None = None,
    pad_align_x: str = "center",
    pad_align_y: str = "center",
    output_format: str | None = None,
    quality: int = 85,
    rotate_deg: int = 0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    grayscale: bool = False,
    progress_callback=None,
) -> tuple[int, int, list[str], str]:
    """
    Process all images and save to output_folder (or next to each source if output_to_source).
    Returns (success_count, fail_count, error_messages, notice). notice is a short UX message
    (e.g. about automatic suffixing) or empty string.
    """
    if input_files:
        paths = list(input_files)
    elif input_folder and Path(input_folder).is_dir():
        paths = get_image_paths(input_folder)
    else:
        paths = []
    if not paths:
        return 0, 0, ["No image files to process. Use a folder or paste a list of file paths."], ""
    if not output_to_source and not output_folder:
        return 0, 0, ["Output folder is required when not using “Same as source”."], ""

    notice = ""
    suffix_used = False
    effective_format = "png" if (pad_to or pad_ratio) else output_format
    success = 0
    failed = 0
    errors: list[str] = []

    if output_to_source:
        stem_override = (output_stem or "").strip() or None
        for i, path in enumerate(paths):
            parent = path.parent
            stem = stem_override if stem_override else path.stem
            ext = _output_extension(path, effective_format)
            out_path, used = get_output_path(parent, stem, ext, path)
            if used:
                suffix_used = True
            err = process_image(
                path,
                parent,
                output_path=out_path,
                resize=resize,
                max_width=max_width,
                max_height=max_height,
                keep_aspect=keep_aspect,
                pad_to=pad_to,
                pad_ratio=pad_ratio,
                pad_align_x=pad_align_x,
                pad_align_y=pad_align_y,
                output_format=output_format,
                quality=quality,
                rotate_deg=rotate_deg,
                flip_horizontal=flip_horizontal,
                flip_vertical=flip_vertical,
                grayscale=grayscale,
            )
            if err:
                failed += 1
                errors.append(f"{path.name}: {err}")
            else:
                success += 1
            if progress_callback:
                progress_callback(i + 1, len(paths))
        if suffix_used:
            notice = "Some filenames were given a suffix (_1, _2, …) to avoid overwriting."
    else:
        os.makedirs(output_folder, exist_ok=True)
        output_dir = Path(output_folder)
        stem_override = (output_stem or "").strip() or None
        for i, path in enumerate(paths):
            if stem_override:
                ext = _output_extension(path, effective_format)
                out_path, used = get_next_path_for_stem(output_dir, stem_override, ext)
                if used:
                    suffix_used = True
                err = process_image(
                    path,
                    output_dir,
                    output_path=out_path,
                    resize=resize,
                    max_width=max_width,
                    max_height=max_height,
                    keep_aspect=keep_aspect,
                    pad_to=pad_to,
                    pad_ratio=pad_ratio,
                    pad_align_x=pad_align_x,
                    pad_align_y=pad_align_y,
                    output_format=output_format,
                    quality=quality,
                    rotate_deg=rotate_deg,
                    flip_horizontal=flip_horizontal,
                    flip_vertical=flip_vertical,
                    grayscale=grayscale,
                )
            else:
                err = process_image(
                    path,
                    output_dir,
                    resize=resize,
                    max_width=max_width,
                    max_height=max_height,
                    keep_aspect=keep_aspect,
                    pad_to=pad_to,
                    pad_ratio=pad_ratio,
                    pad_align_x=pad_align_x,
                    pad_align_y=pad_align_y,
                    output_format=output_format,
                    quality=quality,
                    rotate_deg=rotate_deg,
                    flip_horizontal=flip_horizontal,
                    flip_vertical=flip_vertical,
                    grayscale=grayscale,
                )
            if err:
                failed += 1
                errors.append(f"{path.name}: {err}")
            else:
                success += 1
            if progress_callback:
                progress_callback(i + 1, len(paths))
        if suffix_used:
            notice = "Some filenames were given a suffix (_1, _2, …) to avoid overwriting."

    return success, failed, errors, notice
