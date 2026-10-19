"""Pillow (PIL) — practical single-file examples.

Install:  pip install pillow
Run:      python pillow_examples.py

Creates and manipulates images without external assets: drawing, resizing,
cropping, rotating, filters, colour operations, blending, text, and GIF export.
Generated files go to ``output/``.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

OUTPUT = Path(__file__).resolve().parent / "output"


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def save(image: Image.Image, name: str, **kwargs) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    image.save(path, **kwargs)
    print(f"saved: {path}  mode={image.mode} size={image.size}")
    return path


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Use a common system font if available, otherwise Pillow's bitmap font."""
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# 1. Creating images and basic properties
# ---------------------------------------------------------------------------
def creation() -> Image.Image:
    section("1. Creating images")

    solid = Image.new("RGB", (400, 300), color=(30, 80, 160))
    print("solid:", solid.mode, solid.size, solid.getpixel((0, 0)))
    save(solid, "01_solid.png")

    rgba = Image.new("RGBA", (300, 300), (255, 180, 0, 128))
    print("rgba with alpha:", rgba.getpixel((10, 10)))
    save(rgba, "02_rgba.png")

    # Gradients via per-pixel access (small images only; numpy is faster)
    gradient = Image.new("RGB", (400, 200))
    pixels = gradient.load()
    for x in range(gradient.width):
        for y in range(gradient.height):
            pixels[x, y] = (x * 255 // gradient.width, y * 255 // gradient.height, 128)
    save(gradient, "03_gradient.png")

    # Copy and crop
    cropped = gradient.crop((50, 25, 250, 150))
    save(cropped, "04_crop.png")

    print("format:", solid.format, "info:", solid.info)
    print("getbbox:", gradient.getbbox())
    return gradient


# ---------------------------------------------------------------------------
# 2. Drawing shapes and text
# ---------------------------------------------------------------------------
def drawing() -> Image.Image:
    section("2. Drawing shapes, lines, and text")

    image = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(image)

    draw.rectangle((20, 20, 180, 120), fill=(70, 130, 180), outline="black", width=3)
    draw.ellipse((220, 20, 360, 120), fill=(255, 165, 0), outline="black", width=3)
    draw.polygon([(430, 20), (520, 120), (380, 120)], fill=(60, 179, 113), outline="black")
    draw.line([(20, 160), (580, 160)], fill="red", width=4)
    draw.line([(20, 180), (180, 260), (340, 190), (580, 260)], fill="purple", width=3, joint="curve")

    draw.arc((20, 280, 160, 380), start=0, end=270, fill="black", width=3)
    draw.chord((180, 280, 300, 380), start=30, end=150, fill=(200, 200, 255), outline="black")
    draw.pieslice((320, 280, 440, 380), start=200, end=340, fill=(255, 200, 200), outline="black")

    draw.rounded_rectangle((460, 280, 570, 370), radius=12, fill=(220, 220, 220), outline="black", width=2)

    font = load_font(28)
    draw.text((20, 200), "Pillow drawing examples", font=font, fill="black")
    draw.text((420, 150), "RGB", font=font, fill=(30, 80, 160))
    draw.multiline_text((20, 250), "multi-line\ntext output", font=load_font(20), fill="gray", spacing=6)

    # Measure text to centre it without relying on font-specific anchors
    label = "centered"
    label_font = load_font(18)
    left, top, right, bottom = draw.textbbox((0, 0), label, font=label_font)
    draw.text((300 - (right - left) / 2, 230 - (bottom - top) / 2), label, font=label_font, fill="black")

    save(image, "05_drawing.png")
    return image


# ---------------------------------------------------------------------------
# 3. Geometry: resize, thumbnail, rotate, transpose, paste
# ---------------------------------------------------------------------------
def geometry(base: Image.Image) -> None:
    section("3. Resizing, rotating, and compositing")

    resized = base.resize((300, 150), resample=Image.Resampling.LANCZOS)
    save(resized, "06_resize.png")

    thumbnail = base.copy()
    thumbnail.thumbnail((120, 120))  # preserves aspect ratio, in place
    print("thumbnail size:", thumbnail.size)
    save(thumbnail, "07_thumbnail.png")

    save(base.rotate(30, expand=True, fillcolor="white"), "08_rotate.png")
    save(base.transpose(Image.Transpose.FLIP_LEFT_RIGHT), "09_flip.png")
    save(base.transpose(Image.Transpose.ROTATE_90), "10_rotate90.png")

    # Paste with a mask for transparency
    canvas = Image.new("RGB", (700, 300), "white")
    canvas.paste(base.resize((350, 170)), (10, 60))
    circle_mask = Image.new("L", (200, 200), 0)
    ImageDraw.Draw(circle_mask).ellipse((0, 0, 200, 200), fill=255)
    patch = base.resize((200, 200))
    canvas.paste(patch, (420, 50), circle_mask)
    save(canvas, "11_paste_mask.png")

    # Fit/crop/pad helpers
    save(ImageOps.fit(base, (200, 200), method=Image.Resampling.LANCZOS), "12_fit_square.png")
    save(ImageOps.expand(base, border=20, fill="yellow"), "13_expand.png")
    save(ImageOps.pad(base, (500, 200), color="lightgray"), "14_pad.png")


# ---------------------------------------------------------------------------
# 4. Colour conversions and adjustments
# ---------------------------------------------------------------------------
def colour() -> None:
    section("4. Colour modes and adjustments")

    image = Image.new("RGB", (300, 300), (200, 90, 40))
    ImageDraw.Draw(image).rectangle((50, 50, 250, 250), fill=(40, 160, 200))

    save(image.convert("L"), "15_grayscale.png")
    save(image.convert("1"), "16_bilevel.png")
    save(image.convert("P", palette=Image.Palette.ADAPTIVE), "17_palette.png")
    save(image.convert("CMYK"), "18_cmyk.png")

    save(ImageEnhance.Brightness(image).enhance(1.6), "19_brightness.png")
    save(ImageEnhance.Contrast(image).enhance(0.5), "20_contrast.png")
    save(ImageEnhance.Color(image).enhance(0.0), "21_desaturate.png")
    save(ImageEnhance.Sharpness(image).enhance(2.0), "22_sharpness.png")

    save(ImageOps.autocontrast(image), "23_autocontrast.png")
    save(ImageOps.equalize(image), "24_equalize.png")
    save(ImageOps.invert(image), "25_invert.png")
    save(ImageOps.posterize(image, bits=2), "26_posterize.png")
    save(ImageOps.solarize(image, threshold=100), "27_solarize.png")

    print("histogram length per band:", [len(channel) for channel in image.histogram()[:3]])


# ---------------------------------------------------------------------------
# 5. Filters
# ---------------------------------------------------------------------------
def filters(base: Image.Image) -> None:
    section("5. Convolution filters and blurring")

    save(base.filter(ImageFilter.GaussianBlur(radius=4)), "28_gaussian_blur.png")
    save(base.filter(ImageFilter.BoxBlur(5)), "29_box_blur.png")
    save(base.filter(ImageFilter.SHARPEN), "30_sharpen.png")
    save(base.filter(ImageFilter.EDGE_ENHANCE_MORE), "31_edge_enhance.png")
    save(base.filter(ImageFilter.FIND_EDGES), "32_find_edges.png")
    save(base.filter(ImageFilter.EMBOSS), "33_emboss.png")
    save(base.filter(ImageFilter.CONTOUR), "34_contour.png")

    # Manual 3x3 convolution kernel (edge detection)
    kernel = ImageFilter.Kernel(
        size=(3, 3),
        kernel=(-1, -1, -1, -1, 8, -1, -1, -1, -1),
        scale=1,
        offset=128,
    )
    save(base.convert("L").filter(kernel), "35_custom_kernel.png")

    # Median filter removes salt-and-pepper noise
    noisy = base.copy()
    draw = ImageDraw.Draw(noisy)
    for i in range(0, noisy.width, 7):
        draw.point((i, (i * 13) % noisy.height), fill="white")
    save(noisy.filter(ImageFilter.MedianFilter(size=3)), "36_median.png")


# ---------------------------------------------------------------------------
# 6. Arithmetic and blending
# ---------------------------------------------------------------------------
def blending(base: Image.Image) -> None:
    section("6. ImageChops arithmetic")

    inverted = ImageOps.invert(base.convert("RGB"))
    save(ImageChops.difference(base.convert("RGB"), inverted), "37_difference.png")
    save(ImageChops.blend(base.convert("RGB"), inverted, alpha=0.35), "38_blend.png")
    save(ImageChops.multiply(base.convert("RGB"), inverted), "39_multiply.png")
    save(ImageChops.screen(base.convert("RGB"), inverted), "40_screen.png")
    save(ImageChops.add(base.convert("RGB"), inverted, scale=2.0), "41_add.png")
    save(ImageChops.overlay(base.convert("RGB"), inverted), "42_overlay.png")

    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).ellipse((40, 20, base.width - 40, base.height - 20), fill=255)
    composited = Image.composite(inverted, base.convert("RGB"), mask)
    save(composited, "43_composite_mask.png")


# ---------------------------------------------------------------------------
# 7. Text cards and watermarks
# ---------------------------------------------------------------------------
def text_and_watermark(base: Image.Image) -> None:
    section("7. Text cards and semi-transparent watermarks")

    card = Image.new("RGB", (800, 450), (18, 24, 38))
    draw = ImageDraw.Draw(card)
    draw.text((50, 120), "Program Dataset", font=load_font(54), fill=(240, 240, 250))
    draw.text((50, 200), "Pillow examples", font=load_font(28), fill=(120, 200, 255))
    draw.line((50, 260, 500, 260), fill=(120, 200, 255), width=2)
    draw.text((50, 290), "Images generated entirely in code.", font=load_font(20), fill=(180, 190, 210))
    save(card, "44_text_card.png")

    watermark = Image.new("RGBA", base.size, (0, 0, 0, 0))
    watermark_draw = ImageDraw.Draw(watermark)
    watermark_font = load_font(48)
    text = "DATASET"
    left, top, right, bottom = watermark_draw.textbbox((0, 0), text, font=watermark_font)
    watermark_draw.text(
        (base.width // 2 - (right - left) / 2, base.height // 2 - (bottom - top) / 2),
        text,
        font=watermark_font,
        fill=(255, 255, 255, 80),
    )
    watermarked = Image.alpha_composite(base.convert("RGBA"), watermark)
    save(watermarked.convert("RGB"), "45_watermark.png")

    # Drop shadow: blur a black silhouette and paste the original on top
    shadow = Image.new("RGBA", (base.width + 40, base.height + 40), (0, 0, 0, 0))
    silhouette = Image.new("RGBA", base.size, (0, 0, 0, 120))
    shadow.paste(silhouette, (25, 25))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    shadow.alpha_composite(base.convert("RGBA"), (20, 20))
    save(shadow.convert("RGB"), "46_drop_shadow.png")


# ---------------------------------------------------------------------------
# 8. Animated GIF
# ---------------------------------------------------------------------------
def animation() -> None:
    section("8. Animated GIF export")

    frames = []
    for index in range(12):
        frame = Image.new("RGB", (240, 240), (15, 20, 35))
        draw = ImageDraw.Draw(frame)
        x = 30 + index * 14
        y = 120 + int(60 * ((index / 11) ** 2))
        draw.ellipse((x - 18, y - 18, x + 18, y + 18), fill=(90, 200, 255))
        draw.rectangle((0, 210, 240, 240), fill=(30, 45, 70))
        draw.text((12, 12), f"frame {index + 1:02d}", font=load_font(16), fill="white")
        frames.append(frame)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "47_animation.gif"
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=90, loop=0)
    print("saved:", path, f"({path.stat().st_size:,} bytes, {len(frames)} frames)")


# ---------------------------------------------------------------------------
# 9. Reading metadata and converting formats
# ---------------------------------------------------------------------------
def io_and_metadata() -> None:
    section("9. Format conversion and metadata")

    source = OUTPUT / "05_drawing.png"
    if not source.exists():
        print("source drawing missing; skipping conversion")
        return

    with Image.open(source) as image:
        print("format:", image.format, "mode:", image.mode, "size:", image.size)
        print("info keys:", list(image.info))
        image.convert("RGB").save(OUTPUT / "48_converted.jpg", quality=88, optimize=True)
        image.save(OUTPUT / "49_converted.webp", quality=85)
        image.save(OUTPUT / "50_converted.bmp")

    # EXIF-aware loading (generated images have no EXIF, so this is a no-op)
    with Image.open(source) as image:
        oriented = ImageOps.exif_transpose(image)
        print("exif transpose size:", oriented.size)

    for name in ("48_converted.jpg", "49_converted.webp", "50_converted.bmp"):
        path = OUTPUT / name
        if path.exists():
            with Image.open(path) as reopened:
                print(f"{name}: {reopened.format} {reopened.size} {path.stat().st_size:,} bytes")


def main() -> None:
    print("Pillow version:", __import__("PIL").__version__)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    base = creation()
    drawing()
    geometry(base)
    colour()
    filters(base)
    blending(base)
    text_and_watermark(base)
    animation()
    io_and_metadata()

    print("\nAll Pillow example sections completed.")


if __name__ == "__main__":
    main()
