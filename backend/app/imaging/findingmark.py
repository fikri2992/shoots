"""A Finding, drawn on the pixels it was computed from.

Every Finding carries its figure so the reader can check it — "8.35% of the
frame is above 250 of 255" — but a percentage is only checkable against a
histogram nobody has open. Marked on the frame, the number becomes something
the photographer can see is true, which is the whole difference between a
measurement and an opinion with a number printed beside it.

Blown highlights are drawn as **zebras**: diagonal stripes over the clipped
area, the way every mirrorless body has shown them in the viewfinder for
twenty years. The convention does not need explaining to the reader.

The mask is recomputed here from the threshold ``imaging/tone.py`` measured
with, never stored, so the picture and the figure cannot drift apart. Only
findings whose evidence is a region of pixels can be drawn, and the rest return
the frame unchanged — the way ``domain/motion.py`` stays silent about the
moves translation cannot see. A finding that cannot draw itself is not a lesser
finding; it has nothing to point at. Camera shake is a statement about the
shutter, and no region of the frame is the shake.
"""

import numpy as np
from PIL import Image

from app.domain import findings
from app.domain.entities import Finding
from app.imaging.tone import CLIP_HIGH

#: Zebra red. Distinct from the overlay's findings and its one instruction: a
#: finding is neither something the panel saw nor something to do, it is
#: something wrong.
ZEBRA = (255, 64, 64)
#: Stripe geometry as a fraction of the long edge, so a 4000 px frame and a
#: 1200 px one show stripes of the same visual width.
STRIPE_PERIOD = 0.014
STRIPE_DUTY = 0.45

#: Findings with a region to point at. Everything else draws nothing.
DRAWABLE = frozenset({findings.BLOWN_HIGHLIGHTS})


def _stripes(width: int, height: int) -> np.ndarray:
    """A 45° stripe mask over the whole frame."""
    period = max(4, round(max(width, height) * STRIPE_PERIOD))
    x = np.arange(width)[None, :]
    y = np.arange(height)[:, None]
    return ((x + y) % period) < max(1, round(period * STRIPE_DUTY))


def blown_mask(image: Image.Image) -> np.ndarray:
    """Where the highlights ran out, by the arithmetic that measured them.

    Rec. 601 luminance above ``CLIP_HIGH``, matching ``imaging/tone.py``
    exactly. If this disagreed with ``Tone.clipped_high`` the artifact would
    be arguing with its own caption.
    """
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    return luma > CLIP_HIGH


def mark(image: Image.Image, shot_findings: list[Finding]) -> Image.Image:
    """The frame with every drawable finding marked. Others pass through."""
    if not any(finding.finding_id in DRAWABLE for finding in shot_findings):
        return image
    out = image
    for finding in shot_findings:
        if finding.finding_id == findings.BLOWN_HIGHLIGHTS:
            out = _draw_blown(out)
    return out


def _draw_blown(image: Image.Image) -> Image.Image:
    pixels = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    height, width = pixels.shape[:2]
    pixels[blown_mask(image) & _stripes(width, height)] = ZEBRA
    return Image.fromarray(pixels, "RGB")
