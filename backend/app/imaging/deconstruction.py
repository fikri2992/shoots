"""Image-led social pages, plus a genuinely clean, uncropped JPEG ending."""

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.domain.deconstruction import DETAIL_ASPECT
from app.domain.entities import (
    DeconstructionEvidence,
    DeconstructionPage,
    DeconstructionPageKind,
    GridSpec,
    VisualArtifactAuthority,
    VisualArtifactKind,
    VisualEvidenceArtifact,
)
from app.domain.grid import Grid
from app.imaging.canvas import font_for

WIDTH = 1080
HEIGHT = 1350
INK = (16, 17, 16)
PAPER = (244, 240, 229)
MUTED = (167, 169, 157)
AMBER = (222, 182, 107)
RENDER_VERSION = "deconstruction-social-render-5"


def detail_contact_sheet(
    original: Image.Image, evidence: list[DeconstructionEvidence], grid_spec: GridSpec | None
) -> Image.Image | None:
    """Show the writer the exact existing crops it may select, not invented geometry."""
    eligible = [item for item in evidence if item.cells]
    if not eligible or grid_spec is None:
        return None
    grid = Grid(grid_spec.cols, grid_spec.rows, original.width, original.height)
    tile_width, tile_height = 512, 390
    rows = (len(eligible) + 1) // 2
    out = Image.new("RGB", (tile_width * 2, rows * tile_height), INK)
    draw = ImageDraw.Draw(out)
    for index, item in enumerate(eligible):
        x, y = (index % 2) * tile_width, (index // 2) * tile_height
        crop = original.crop(grid.context_bounds(item.cells, DETAIL_ASPECT).as_tuple())
        draw.text((x + 16, y + 6), "DETAIL", font=font_for(14), fill=AMBER)
        draw.text((x + 16, y + 24), item.id, font=font_for(18), fill=PAPER)
        _contain(out, crop, (x + 12, y + 48, x + tile_width - 12, y + tile_height - 12))
    return out


def artifact_contact_sheet(
    evidence: list[DeconstructionEvidence], images: dict[str, Image.Image]
) -> Image.Image | None:
    """Show the exact stored artifacts, not reconstructed or guessed overlays."""
    eligible = [item for item in evidence if item.visual_artifact and item.id in images]
    if not eligible:
        return None
    tile_width, tile_height = 512, 560
    out = Image.new("RGB", (tile_width * 2, ((len(eligible) + 1) // 2) * tile_height), INK)
    draw = ImageDraw.Draw(out)
    for index, item in enumerate(eligible):
        x, y = (index % 2) * tile_width, (index // 2) * tile_height
        draw.text((x + 16, y + 8), "ARTIFACT", font=font_for(16), fill=AMBER)
        draw.text((x + 16, y + 30), item.id, font=font_for(19), fill=PAPER)
        _contain(out, images[item.id], (x + 12, y + 68, x + tile_width - 12, y + tile_height - 12))
    return out


def render(
    page: DeconstructionPage,
    images: list[Image.Image],
    index: int,
    total: int,
    grid_spec: GridSpec | None = None,
    *,
    artifact_image: Image.Image | None = None,
) -> Image.Image:
    if not images:
        raise ValueError("A story page requires the selected Shot.")
    original = images[0].convert("RGB")
    if page.kind is DeconstructionPageKind.CLEAN:
        # Return before any fitting, drawing, framing, text or page numbering.
        return original.copy()

    out = Image.new("RGB", (WIDTH, HEIGHT), INK)
    draw = ImageDraw.Draw(out)
    if page.kind is DeconstructionPageKind.COVER:
        _contain(out, original, (32, 32, 1048, 882))
        _text(draw, page.title, (64, 926, 1016, 1076), 68, 44, PAPER, serif=True)
        _text(draw, page.claim, (64, 1104, 1016, 1264), 38, 30, PAPER)
    elif page.visual_layer == "artifact":
        if page.visual_artifact is None or artifact_image is None:
            raise ValueError(
                "The selected visual artifact is unavailable. No substitute was drawn."
            )
        _render_artifact_page(out, draw, page, original, artifact_image)
    else:
        _text(draw, page.title, (64, 58, 1016, 202), 60, 42, PAPER, serif=True)
        image = original
        if page.detail_cells:
            if grid_spec is None:
                raise ValueError("A detail crop requires the Shot's stored grid.")
            grid = Grid(grid_spec.cols, grid_spec.rows, original.width, original.height)
            image = original.crop(grid.context_bounds(page.detail_cells, DETAIL_ASPECT).as_tuple())
        draw.text(
            (64, 215),
            "DETAIL" if page.detail_cells else "FULL FRAME",
            font=font_for(20),
            fill=AMBER,
        )
        _contain(out, image, (32, 260, 1048, 990))
        _text(draw, page.claim, (64, 1032, 1016, 1268), 40, 30, PAPER)
    draw.line((64, 1294, 1016, 1294), fill=(58, 60, 52), width=1)
    draw.text((64, 1308), "A VISUAL STORY", font=font_for(18), fill=MUTED)
    draw.text(
        (1016, 1308), f"{index:02d} / {total:02d}", font=font_for(18), fill=MUTED, anchor="ra"
    )
    return out


def _render_artifact_page(
    out: Image.Image,
    draw: ImageDraw.ImageDraw,
    page: DeconstructionPage,
    original: Image.Image,
    artifact_image: Image.Image,
) -> None:
    artifact = page.visual_artifact
    if artifact is None:
        raise ValueError("A visual artifact page requires its stored legend.")
    label, legend = artifact_presentation(artifact)
    _text(draw, page.title, (64, 58, 1016, 202), 60, 42, PAPER, serif=True)
    if original.width < original.height:
        # Portrait Shots use the width that a single contained frame leaves empty.
        boxes = ((32, 256, 528, 938), (552, 256, 1048, 938))
        draw.text((48, 222), "ORIGINAL", font=font_for(20), fill=MUTED)
        draw.text((568, 222), label, font=font_for(20), fill=AMBER)
    else:
        boxes = ((32, 246, 1048, 562), (32, 610, 1048, 926))
        draw.text((48, 210), "ORIGINAL", font=font_for(20), fill=MUTED)
        draw.text((48, 576), label, font=font_for(20), fill=AMBER)
    _contain(out, original, boxes[0])
    _contain(out, artifact_image, boxes[1])
    authority = (
        "Measured map" if artifact.authority is VisualArtifactAuthority.MEASURED else "Visual read"
    )
    _text(draw, f"{authority}. {legend}", (64, 964, 1016, 1042), 25, 21, MUTED)
    _text(draw, page.claim, (64, 1070, 1016, 1268), 38, 28, PAPER)


def artifact_presentation(artifact: VisualEvidenceArtifact) -> tuple[str, str]:
    """Plain legends for existing encodings, never a new interpretation of the Shot."""
    kind = artifact.kind
    if kind is VisualArtifactKind.HUE_MASK:
        if (
            artifact.metrics.get("primary_group") == "warm"
            and artifact.metrics.get("secondary_group") == "cool"
        ):
            return "COLOUR MAP", "Cyan marks warm colours; violet marks cool colours."
        if artifact.metrics.get("secondary_group"):
            return "COLOUR MAP", "Cyan and violet highlight measured colour groups."
        return "COLOUR MAP", "Cyan highlights a measured colour group."
    captions = {
        VisualArtifactKind.LUMINANCE_MAP: (
            "LIGHT MAP",
            "Blue marks darker areas; yellow marks brighter areas.",
        ),
        VisualArtifactKind.SATURATION_MAP: (
            "COLOUR INTENSITY",
            "Blue is less saturated; yellow is more saturated.",
        ),
        VisualArtifactKind.SHARPNESS_MAP: (
            "DETAIL MAP",
            "Blue: lower local contrast. Yellow: higher. This does not measure depth.",
        ),
        VisualArtifactKind.VERIFIED_PATHS: (
            "PATH GUIDE",
            "Cyan follows pixel-supported paths. "
            "Any pale connector points to a model-located target.",
        ),
        VisualArtifactKind.SUBJECT_CONTOUR: (
            "SUBJECT GUIDE",
            "Cyan marks a computer-refined region, not a guaranteed subject outline.",
        ),
    }
    return captions.get(kind, ("VISUAL GUIDE", artifact.legend))


def _contain(out: Image.Image, image: Image.Image, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    fitted = ImageOps.contain(image, (right - left, bottom - top), Image.Resampling.LANCZOS)
    out.paste(
        fitted,
        (left + (right - left - fitted.width) // 2, top + (bottom - top - fitted.height) // 2),
    )


def _font(size: int, serif: bool) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if serif:
        for name in ("georgia.ttf", "DejaVuSerif.ttf", "Times New Roman.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
    return font_for(size)


def _text(
    draw: ImageDraw.ImageDraw,
    value: str,
    box: tuple[int, int, int, int],
    preferred: int,
    minimum: int,
    colour: tuple[int, int, int],
    *,
    serif: bool = False,
) -> None:
    left, top, right, bottom = box
    for size in range(preferred, minimum - 1, -2):
        font = _font(size, serif)
        lines = _wrap(draw, value, font, right - left)
        step = round(size * 1.28)
        if (
            lines
            and len(lines) * step <= bottom - top
            and all(draw.textlength(line, font=font) <= right - left for line in lines)
        ):
            for index, line in enumerate(lines):
                draw.text((left, top + index * step), line, font=font, fill=colour, anchor="lt")
            return
    # Silently taking the first N lines changes the model's claim.
    raise ValueError("Story copy exceeds its layout. No text was truncated.")


def _wrap(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    width: int,
) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if not line or draw.textlength(candidate, font=font) <= width:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines
