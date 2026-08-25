"""A fault the reader can see is true.

The figure and the picture come from the same threshold, so these tests pin
them against each other: whatever share ``imaging/tone.py`` reports as blown
is the share ``faultmark`` stripes, give or take the stripe duty cycle.
"""

import numpy as np
from PIL import Image, ImageDraw

from app.domain import faults
from app.domain.entities import Analysis, Fault, TechniqueEvidence
from app.imaging import faultmark
from app.imaging.tone import measure
from app.services import scribe

SIZE = (240, 160)


def sky_and_ground() -> Image.Image:
    """A blown sky over a mid-grey ground: a quarter of the frame clipped."""
    image = Image.new("RGB", SIZE, (128, 128, 128))
    ImageDraw.Draw(image).rectangle((0, 0, SIZE[0], SIZE[1] // 4), fill=(255, 255, 255))
    return image


def blown_fault() -> Fault:
    return Fault(fault_id=faults.BLOWN_HIGHLIGHTS, what="Blown.", why="25.0% above 250 of 255")


def test_the_mask_is_the_same_arithmetic_the_measurement_used():
    image = sky_and_ground()
    share = float(faultmark.blown_mask(image).mean()) * 100
    assert abs(share - measure(image).clipped_high) < 0.5


def test_zebras_land_only_on_the_blown_area():
    image = sky_and_ground()
    marked = faultmark.mark(image, [blown_fault()])
    before = np.asarray(image, dtype=np.int16)
    after = np.asarray(marked, dtype=np.int16)
    changed = np.any(before != after, axis=-1)
    assert changed.any(), "nothing was marked"
    # Every changed pixel was clipped, and the ground is untouched.
    assert not (changed & ~faultmark.blown_mask(image)).any()
    assert not changed[SIZE[1] // 2 :, :].any()


def test_the_stripes_are_stripes_and_not_a_fill():
    """A solid block would hide the very detail the reader is being shown."""
    image = sky_and_ground()
    marked = faultmark.mark(image, [blown_fault()])
    changed = np.any(np.asarray(image, dtype=np.int16) != np.asarray(marked, dtype=np.int16), -1)
    blown = faultmark.blown_mask(image)
    covered = changed.sum() / blown.sum()
    assert 0.2 < covered < 0.8, covered


def test_a_fault_with_nothing_to_point_at_draws_nothing():
    """Camera shake is a statement about the shutter, not about a region."""
    image = sky_and_ground()
    shake = Fault(fault_id=faults.CAMERA_SHAKE, what="Shake.", why="1/40 s under 1/46 s")
    assert faultmark.mark(image, [shake]) is image
    assert faultmark.mark(image, []) is image


def test_a_clean_frame_is_returned_untouched():
    clean = Image.new("RGB", SIZE, (128, 128, 128))
    marked = faultmark.mark(clean, [blown_fault()])
    assert not np.any(np.asarray(clean) != np.asarray(marked))


# --- what the file is called -------------------------------------------------


def analysis(*, faults_: list[Fault], techniques: list[str], score: int = 7) -> Analysis:
    return Analysis(
        shot_id="s",
        user_id="u",
        model="m",
        score=score,
        faults=faults_,
        techniques=[TechniqueEvidence(technique_id=t, confidence=0.9) for t in techniques],
    )


def test_an_uncorroborated_sighting_does_not_get_to_name_the_file():
    """One lens saw panning and no other did. That is not something to greet
    the photographer with, so the fault - which arithmetic settled - names the
    file instead."""
    found = scribe.review_finding(analysis(faults_=[blown_fault()], techniques=["panning"]))
    assert found == "highlights blown to white"


def test_a_corroborated_sighting_names_the_file_ahead_of_the_fault():
    a = analysis(faults_=[blown_fault()], techniques=["panning"])
    a.techniques[0].agreement = 2
    assert scribe.review_finding(a) == "panning"


def test_a_clean_frame_is_named_for_what_it_does():
    assert scribe.review_finding(analysis(faults_=[], techniques=["panning"])) == "panning"


def test_the_score_is_the_last_resort_and_never_the_headline():
    """It is one number for the whole photograph; nothing else being available
    is the only reason it appears."""
    assert scribe.review_finding(analysis(faults_=[], techniques=[])) == "7 of 10"


def test_the_caption_leads_with_what_is_there_then_what_is_wrong():
    """This order was the other way round while the product was a critic. It is
    for a hobbyist now, who stops opening an app that greets them with a defect
    every time — so praise leads and the fault follows, and neither is dropped."""
    a = analysis(faults_=[blown_fault()], techniques=["panning"])
    assert scribe.review_title(a, None, None) == "Panning · Highlights blown to white"


def test_the_body_carries_every_fault_with_its_figure_and_no_element_scores():
    a = analysis(faults_=[blown_fault()], techniques=["panning"])
    a.elements = {"impact": 8, "composition": 8, "lighting": 8, "technical": 8, "story": 8}
    body = "\n".join(scribe.review_body(a, None, grid=None))
    assert "25.0% above 250 of 255" in body
    # The five elements correlate at r = 0.89; printing them prints one number
    # five times (docs/research-findings.md, section 1).
    assert "impact" not in body and "/10" not in body
