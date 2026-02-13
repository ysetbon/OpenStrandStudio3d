"""
Generate the Windows .ico from the gray icon source.

This keeps installer shortcuts, Start menu entries, and the installed app icon
using the same source artwork.
"""

from pathlib import Path
import shutil
import sys

try:
    from PIL import Image, ImageFilter
except ImportError:
    sys.exit("Pillow is required. Install with: pip install pillow")


ICON_SIZES = [
    (16, 16),
    (24, 24),
    (32, 32),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
]


def _resample_filter():
    if hasattr(Image, "Resampling"):
        return Image.Resampling.LANCZOS
    return Image.LANCZOS


def _tune_for_small_sizes(frame: Image.Image, size: int) -> Image.Image:
    # Small shell icon slots benefit from a light unsharp pass.
    if size <= 48:
        return frame.filter(ImageFilter.UnsharpMask(radius=0.9, percent=180, threshold=1))
    if size <= 96:
        return frame.filter(ImageFilter.UnsharpMask(radius=1.0, percent=140, threshold=1))
    return frame


def generate_windows_ico(source_png: Path, output_ico: Path) -> None:
    src = Image.open(source_png).convert("RGBA")
    resample = _resample_filter()

    rendered = {}
    for width, height in ICON_SIZES:
        frame = src.resize((width, height), resample)
        frame = _tune_for_small_sizes(frame, width)
        rendered[(width, height)] = frame

    ordered = sorted(ICON_SIZES, key=lambda size: size[0], reverse=True)
    base = rendered[ordered[0]]
    extras = [rendered[size] for size in ordered[1:]]

    # Windows may lock existing .ico files (icon cache); delete first.
    if output_ico.exists():
        output_ico.unlink()

    base.save(output_ico, format="ICO", append_images=extras)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    source_png = base_dir / "openstrandstudio3d_icon_gray.png"
    output_ico = base_dir / "openstrandstudio3d_icon_gray.ico"
    legacy_output_ico = base_dir / "openstrandstudio3d_icon.ico"

    if not source_png.exists():
        sys.exit(f"Missing source file: {source_png}")

    generate_windows_ico(source_png, output_ico)
    # Keep legacy filename in sync for compatibility with old references.
    # Windows may lock existing .ico files (icon cache); delete first.
    if legacy_output_ico.exists():
        legacy_output_ico.unlink()
    shutil.copyfile(output_ico, legacy_output_ico)
    print(f"Wrote {output_ico}")
    print(f"Wrote {legacy_output_ico}")


if __name__ == "__main__":
    main()
