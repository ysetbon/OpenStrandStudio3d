"""
Generate the macOS .icns from the gray icon source.

This keeps the app bundle icon, Dock icon, and desktop shortcut
using the same gray artwork as the Windows build.
"""

from pathlib import Path
import struct
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required. Install with: pip install pillow")


# macOS .icns icon types and their sizes
ICNS_TYPES = [
    (b'ic07', 128),   # 128x128 PNG
    (b'ic08', 256),   # 256x256 PNG
    (b'ic09', 512),   # 512x512 PNG
    (b'ic10', 1024),  # 1024x1024 PNG (Retina 512@2x)
    (b'ic11', 32),    # 32x32 PNG (Retina 16@2x)
    (b'ic12', 64),    # 64x64 PNG (Retina 32@2x)
    (b'ic13', 256),   # 256x256 PNG (Retina 128@2x)
    (b'ic14', 512),   # 512x512 PNG (Retina 256@2x)
]


def generate_mac_icns(source_png: Path, output_icns: Path) -> None:
    src = Image.open(source_png).convert("RGBA")

    if hasattr(Image, "Resampling"):
        resample = Image.Resampling.LANCZOS
    else:
        resample = Image.LANCZOS

    entries = []
    for icon_type, size in ICNS_TYPES:
        frame = src.resize((size, size), resample)
        import io
        buf = io.BytesIO()
        frame.save(buf, format="PNG")
        png_data = buf.getvalue()
        # Each entry: type (4 bytes) + length (4 bytes) + data
        entry = icon_type + struct.pack(">I", len(png_data) + 8) + png_data
        entries.append(entry)

    body = b"".join(entries)
    header = b"icns" + struct.pack(">I", len(body) + 8)

    if output_icns.exists():
        output_icns.unlink()

    with open(output_icns, "wb") as f:
        f.write(header + body)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    source_png = base_dir / "openstrandstudio3d_icon_gray.png"
    output_icns = base_dir / "openstrandstudio3d_icon_gray.icns"

    if not source_png.exists():
        sys.exit(f"Missing source file: {source_png}")

    generate_mac_icns(source_png, output_icns)
    print(f"Wrote {output_icns}")


if __name__ == "__main__":
    main()
