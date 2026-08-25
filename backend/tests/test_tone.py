"""Colour and tone are measured, so every test here pins a number.

The images are built to have one obvious right answer — a frame of solid
orange has a colour temperature and a saturation that arithmetic can be held
to — and the domain tests assert what the lenses are told, since routing the
wrong half to the wrong lens is the failure that would quietly undo the panel.
"""

import pytest
from PIL import Image, ImageDraw

from app.domain import tone as rules
from app.domain.entities import Exif, Tone
from app.imaging.tone import measure
from tests.fixtures import jpeg_with_exif

SIZE = (240, 160)


def solid(colour: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", SIZE, colour)


def halves(left: tuple[int, int, int], right: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", SIZE, left)
    ImageDraw.Draw(image).rectangle((SIZE[0] // 2, 0, SIZE[0], SIZE[1]), fill=right)
    return image


def scene(left: tuple[int, int, int], right: tuple[int, int, int]) -> Image.Image:
    """Two hues over a lit neutral ground — what a photograph looks like, and
    what a colour temperature needs: something the light fell on."""
    image = Image.new("RGB", SIZE, (198, 192, 186))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, SIZE[0] // 3, SIZE[1]), fill=left)
    draw.rectangle((SIZE[0] // 3, 0, 2 * SIZE[0] // 3, SIZE[1]), fill=right)
    return image


# --- measurement ----------------------------------------------------------


def test_a_neutral_grey_frame_has_no_saturation_and_no_cast():
    t = measure(solid((128, 128, 128)))
    assert t.saturation == 0.0
    assert t.cast == 0.0
    assert t.hues == []
    # Equal channels sit on the sRGB white point, which is D65.
    assert 6000 <= t.cct_k <= 7000


def test_warm_light_on_a_neutral_measures_warm_and_cool_light_cool():
    """A grey card under tungsten and the same card under shade. This is what
    a colour temperature is a statement about: the light, read off something
    neutral it fell on."""
    warm = measure(solid((205, 190, 175)))
    cool = measure(solid((175, 190, 205)))
    assert warm.cast > 0 and cool.cast < 0
    assert warm.cct_k < rules.DAYLIGHT_K < cool.cct_k


def test_a_frame_too_far_off_the_locus_has_no_temperature():
    """A frame of pure red is a red object, not 2655 K light."""
    from app.imaging.tone import MAX_DUV, chromaticity, duv

    assert abs(duv(*chromaticity((255.0, 0.0, 0.0)))) > MAX_DUV
    assert measure(solid((255, 0, 0))).cct_k is None


def test_a_frame_with_nothing_neutral_and_lit_has_no_temperature():
    """The guard Duv does not give. Saturated orange sits near the Planckian
    locus — that is why tungsten light is orange — so a low-key frame against a
    burnt-orange backdrop passes the Duv test and then reports 1637 K about a
    frame that was nothing of the kind. There is no white in it to balance
    against, and black is not a neutral: it carries no colour at all."""
    black_and_orange = Image.new("RGB", SIZE, (0, 0, 0))
    ImageDraw.Draw(black_and_orange).rectangle((0, 0, SIZE[0], SIZE[1] // 2), fill=(200, 66, 12))
    assert measure(black_and_orange).cct_k is None
    # The rest of the reading survives; only the claim that needs a white does not.
    assert measure(black_and_orange).luma_mean > 0


def test_the_temperature_is_read_off_the_light_not_off_the_frame_average():
    """A neutral wall under warm light, with a large saturated blue object in
    front of it. Averaging the whole frame would let the object drag the
    temperature; the reference pixels are what the light actually fell on."""
    image = Image.new("RGB", SIZE, (205, 190, 175))
    ImageDraw.Draw(image).rectangle((0, 0, SIZE[0] // 2, SIZE[1]), fill=(20, 40, 200))
    assert measure(image).cct_k == measure(solid((205, 190, 175))).cct_k


def test_a_cast_cannot_be_claimed_without_a_temperature():
    """The finding reads ``cct_k``; None has to mean silence, not a default."""
    from app.domain import findings

    assert findings._cast(Tone(cct_k=None, saturation=90.0), set()) is None


def test_saturation_separates_a_grey_frame_from_a_vivid_one():
    assert measure(solid((128, 128, 128))).saturation == 0.0
    assert measure(solid((255, 0, 0))).saturation == 100.0
    assert rules.derive(measure(solid((255, 0, 0)))).palette == "vivid"


def test_clipping_is_counted_at_both_ends():
    white = measure(solid((255, 255, 255)))
    black = measure(solid((0, 0, 0)))
    assert white.clipped_high == 100.0 and white.clipped_low == 0.0
    assert black.clipped_low == 100.0 and black.clipped_high == 0.0


def test_two_opposed_hues_are_measured_as_opposed():
    """Orange against teal is the complementary pair the catalogue names."""
    t = measure(halves((235, 140, 45), (40, 170, 175)))
    assert t.hue_opposition is not None
    assert t.hue_opposition >= rules.COMPLEMENTARY_MIN
    assert rules.harmony_of(t) == "opposed, the complementary relationship"


def test_neighbouring_hues_are_measured_as_analogous():
    t = measure(halves((235, 140, 45), (235, 190, 45)))
    assert t.hue_opposition <= rules.ANALOGOUS_MAX
    assert "analogous" in rules.harmony_of(t)


def test_warm_and_cool_shares_are_of_the_whole_frame_not_of_its_colours():
    """A mostly grey frame with a warm corner is not a warm frame."""
    image = Image.new("RGB", SIZE, (128, 128, 128))
    ImageDraw.Draw(image).rectangle((0, 0, SIZE[0] // 10, SIZE[1] // 10), fill=(240, 140, 30))
    t = measure(image)
    assert t.warm_share < 5.0


def test_an_empty_frame_measures_without_raising():
    assert measure(Image.new("RGB", (1, 1), (0, 0, 0))).clipped_low == 100.0


# --- bands ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("kelvin", "expected"),
    [
        (2000, "candle or sodium light"),
        (3200, "tungsten"),
        (4500, "a warm interior or late golden light"),
        (5500, "early or late daylight"),
        (6000, "midday daylight"),
        (6800, "overcast daylight"),
        (9000, "open shade or a heavy blue cast"),
    ],
)
def test_temperature_bands_name_the_light(kelvin: int, expected: str):
    assert rules.band(kelvin, rules.TEMPERATURE_BANDS) == expected


@pytest.mark.parametrize(
    ("luma", "expected"), [(200, "high key"), (128, "mid key"), (40, "low key")]
)
def test_key_follows_mean_luminance(luma: float, expected: str):
    assert rules.derive(Tone(luma_mean=luma)).key == expected


def test_tonal_range_is_the_spread_between_the_percentiles():
    d = rules.derive(Tone(luma_mean=120, luma_p5=20, luma_p95=230))
    assert d.tonal_range == 210
    assert d.range_band == "the full range"


def test_a_frame_with_no_colour_gets_no_hue_relationship():
    assert "too little colour" in rules.harmony_of(Tone(saturation=4.0, hue_opposition=180))


# --- the sun --------------------------------------------------------------


def _exif_at(when: str, gps: tuple[float, float] | None = (51.5, -0.12)) -> Exif:
    from app.imaging.exif import read_exif

    return read_exif(jpeg_with_exif(when=when, gps=gps))


def test_golden_hour_is_checked_against_the_sun_not_believed():
    """Late June in London: sunset is about 20:21 UTC."""
    assert "golden hour" in rules.solar_context(_exif_at("2026:06:21 20:00:00"))
    noon = rules.solar_context(_exif_at("2026:06:21 12:00:00"))
    assert "not golden or blue hour" in noon and "solar noon" in noon


def test_the_sun_says_nothing_without_a_time_and_a_place():
    assert rules.solar_context(_exif_at("2026:06:21 12:00:00", gps=None)) == ""
    assert rules.solar_context(Exif()) == ""


# --- what each lens is told -----------------------------------------------


def test_the_lens_groups_are_disjoint():
    """The panel is only worth its cost while the three readings are
    independent. Handing every lens the same measurements would buy anchored
    claims with the decorrelation that makes the vote mean anything."""
    t = measure(scene((235, 140, 45), (40, 170, 175)))
    exif = _exif_at("2026:06:21 12:00:00")
    technical, light, palette = rules.technical(t), rules.light(t, exif), rules.palette(t)
    assert set(technical) & set(light) == set()
    assert set(light) & set(palette) == set()
    assert set(palette) & set(technical) == set()


def test_each_lens_gets_the_family_it_owns():
    t = measure(scene((235, 140, 45), (40, 170, 175)))
    assert any("clipped" in line for line in rules.technical(t))
    assert any("colour temperature" in line for line in rules.light(t))
    assert any("saturation" in line for line in rules.palette(t))
    # ... and not the others': temperature is the Composer's, not the Storyteller's.
    assert not any("colour temperature" in line for line in rules.palette(t))
    assert not any("saturation" in line for line in rules.technical(t))


def test_describe_is_the_union_and_carries_no_duplicates():
    t = measure(solid((230, 130, 40)))
    everything = rules.describe(t)
    assert len(everything) == len(set(everything))
    for group in (rules.technical(t), rules.light(t), rules.palette(t)):
        assert set(group) <= set(everything)


def test_nothing_measured_says_nothing():
    assert rules.describe(Tone()) == []
    assert rules.technical(Tone()) == []
