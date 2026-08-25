"""The Tendency Profile: counts first, claims only when the counts carry them."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain import tendency
from app.domain.entities import Analysis, Composition, Exif, GridSpec, Shot, ShotKind, Tone

JAKARTA = (-6.2, 106.8)


def shot(
    sid: str = "s1",
    *,
    subject: tuple[float, float] | None = None,
    cells: int = 0,
    luma: float = 0.0,
    warm: float = 0.0,
    cool: float = 0.0,
    size: tuple[int, int] = (800, 600),
    captured: datetime | None = None,
    located: bool = False,
    pitch: float | None = None,
) -> tuple[Shot, Analysis | None]:
    exif = Exif(captured_at=captured)
    if located:
        exif.latitude, exif.longitude = JAKARTA
    s = Shot(
        id=sid,
        user_id="u1",
        kind=ShotKind.PHOTO,
        drive_file_id=sid,
        filename=f"{sid}.jpg",
        mime_type="image/jpeg",
        exif=exif,
        tone=Tone(luma_mean=luma, warm_share=warm, cool_share=cool),
        grid=GridSpec(cols=8, rows=6, width=size[0], height=size[1]),
        pitch_deg=pitch,
    )
    comp = Composition(subject_cells=[f"C{i}" for i in range(cells)])
    if subject:
        comp.subject_x, comp.subject_y = subject
    analysis = Analysis(shot_id=sid, user_id="u1", model="test", composition=comp)
    return s, analysis


# --- reading one shot -----------------------------------------------------------


@pytest.mark.parametrize(
    ("point", "bucket"),
    [
        ((0.5, 0.5), "centred"),
        ((0.55, 0.52), "centred"),
        ((0.333, 0.333), "off centre"),  # a thirds intersection is not centred
        ((0.1, 0.5), "near the edge"),
    ],
)
def test_placement_reads_the_subject_point(point, bucket):
    s, a = shot(subject=point)
    assert tendency.read_shot(s, a)["placement"] == bucket


def test_framing_is_the_share_of_the_frame_the_subject_covers():
    assert tendency.read_shot(*shot(cells=2))["framing"] == "wide"  # 2 of 48
    assert tendency.read_shot(*shot(cells=8))["framing"] == "medium"
    assert tendency.read_shot(*shot(cells=20))["framing"] == "close"


def test_orientation_comes_from_the_frame_itself():
    assert tendency.read_shot(*shot(size=(800, 600)))["orientation"] == "landscape"
    assert tendency.read_shot(*shot(size=(600, 800)))["orientation"] == "portrait"
    assert tendency.read_shot(*shot(size=(700, 700)))["orientation"] == "square"


def test_palette_needs_a_lean_before_it_names_one():
    assert tendency.read_shot(*shot(warm=30, cool=5))["palette"] == "warm"
    assert tendency.read_shot(*shot(warm=5, cool=30))["palette"] == "cool"
    assert tendency.read_shot(*shot(warm=20, cool=18))["palette"] == "neutral"


def test_an_unmeasured_dimension_is_absent_not_guessed():
    """Tone was never measured on this one. The profile must not invent a
    bucket for it: an absent reading and a reading of 'mid' are different."""
    point = tendency.read_shot(*shot())
    assert "key" not in point and "palette" not in point
    assert "placement" not in point  # no subject point either


def test_light_needs_the_time_and_the_place():
    midday = datetime(2026, 8, 25, 5, 0, tzinfo=UTC)  # noon in Jakarta
    assert "light" not in tendency.read_shot(*shot(captured=midday))
    assert tendency.read_shot(*shot(captured=midday, located=True))["light"] == "open day"


def test_golden_hour_is_a_claim_about_the_sun():
    dusk = datetime(2026, 8, 25, 10, 55, tzinfo=UTC)  # ~17:55 local, near sunset
    assert tendency.read_shot(*shot(captured=dusk, located=True))["light"] == "golden hour"


def test_height_is_silent_without_the_camera():
    """Every shot that arrived through Drive has no pitch. The dimension has to
    stay quiet rather than default to eye level and invent a tendency."""
    assert "height" not in tendency.read_shot(*shot())
    assert tendency.read_shot(*shot(pitch=0.0))["height"] == "eye level"
    assert tendency.read_shot(*shot(pitch=35.0))["height"] == "low"
    assert tendency.read_shot(*shot(pitch=-30.0))["height"] == "high"


# --- the profile ----------------------------------------------------------------


def corpus(n: int, **kwargs) -> list[tuple[Shot, Analysis | None]]:
    return [shot(f"s{i}", **kwargs) for i in range(n)]


def test_one_bucket_for_everything_is_no_exploration():
    profile = tendency.build(corpus(10, subject=(0.5, 0.5)))
    placement = profile.dimensions["placement"]
    assert placement.n == 10
    assert placement.dominant == "centred"
    assert placement.dominant_share == 1.0
    assert placement.exploration == 0.0
    assert placement.narrow is True
    assert placement.unexplored == ("off centre", "near the edge")


def test_an_even_spread_is_full_exploration():
    rows = (
        corpus(4, subject=(0.5, 0.5))
        + [shot(f"b{i}", subject=(0.35, 0.42)) for i in range(4)]
        + [shot(f"c{i}", subject=(0.1, 0.5)) for i in range(4)]
    )
    assert tendency.build(rows).dimensions["placement"].exploration == pytest.approx(1.0)


def test_a_thin_corpus_counts_but_does_not_claim():
    """Five frames cannot carry 'you always centre the subject'."""
    placement = tendency.build(corpus(5, subject=(0.5, 0.5))).dimensions["placement"]
    assert placement.n == 5 and placement.dominant == "centred"
    assert placement.readable is False and placement.narrow is False


def test_unreadable_shots_are_counted_separately_from_buckets():
    rows = corpus(6, subject=(0.5, 0.5)) + corpus(4)  # four with no subject point
    placement = tendency.build(rows).dimensions["placement"]
    assert placement.n == 6 and placement.unreadable == 4


def test_the_narrowest_dimension_is_what_a_challenge_pushes_against():
    """Placement never varies; orientation and key both do."""
    rows = [
        shot(
            f"s{i}",
            subject=(0.5, 0.5),
            luma=40 + i * 12,
            size=(800, 600) if i % 2 else (600, 800),
        )
        for i in range(10)
    ]
    narrowest = tendency.build(rows).narrowest()
    assert narrowest is not None and narrowest.dimension.id == "placement"


def test_a_tie_at_zero_goes_to_the_choice_that_changes_a_photograph_most():
    """A corpus shot entirely in landscape with the subject always centred
    leaves both dimensions at zero exploration. Sorted by name, orientation
    would win every time and the photographer would be told to turn the phone
    sideways forever."""
    profile = tendency.build(corpus(10, subject=(0.5, 0.5), size=(800, 600)))
    assert profile.dimensions["orientation"].exploration == 0.0
    assert profile.dimensions["placement"].exploration == 0.0
    assert profile.narrowest().dimension.id == "placement"


def test_nothing_is_narrow_when_nothing_has_enough_behind_it():
    assert tendency.build(corpus(3, subject=(0.5, 0.5))).narrowest() is None


def test_blind_spots_are_named_rather_than_dropped():
    profile = tendency.build(corpus(10, subject=(0.5, 0.5)))
    spots = " ".join(profile.blind_spots)
    assert "the height you shoot from" in spots
    assert "Shoots camera" in spots
    assert "where you put the subject" not in spots  # this one was readable


# --- taste ----------------------------------------------------------------------


def test_without_keepers_the_profile_knows_no_taste():
    profile = tendency.build(corpus(10, subject=(0.5, 0.5)))
    assert profile.keepers == 0
    assert profile.taste_is_known is False
    assert profile.dimensions["placement"].keeper_lift("centred", profile.keeper_rate) is None


def test_keeper_lift_is_the_photographers_own_verdict():
    """Twelve centred shots kept twice; four low-angle shots kept three times.
    The lift is what makes a challenge 'what you value, underexplored' rather
    than generic advice."""
    rows = [shot(f"c{i}", subject=(0.5, 0.5)) for i in range(12)]
    rows += [shot(f"e{i}", subject=(0.1, 0.5)) for i in range(4)]
    keepers = {"c0", "c1", "e0", "e1", "e2"}
    profile = tendency.build(rows, keepers)
    placement = profile.dimensions["placement"]

    assert profile.keepers == 5 and profile.taste_is_known is True
    assert profile.keeper_rate == pytest.approx(5 / 16)
    centred = placement.keeper_lift("centred", profile.keeper_rate)
    edge = placement.keeper_lift("near the edge", profile.keeper_rate)
    assert centred is not None and edge is not None
    assert edge > 2.0 > centred  # kept far more often than the habit


# --- dwell ----------------------------------------------------------------------


def at(minute: int) -> datetime:
    return datetime(2026, 8, 25, 9, 0, tzinfo=UTC) + timedelta(minutes=minute)


def test_shots_close_in_time_are_one_scene():
    rows = [shot(f"s{i}", captured=at(i)) for i in range(4)]
    worked = tendency.dwell(rows)
    assert worked.scenes == 1 and worked.shots == 4 and worked.longest == 4


def test_a_gap_starts_a_new_scene():
    rows = [shot("a", captured=at(0)), shot("b", captured=at(1)), shot("c", captured=at(30))]
    assert tendency.dwell(rows).scenes == 2


def test_one_frame_and_away_is_the_tendency_with_the_most_advice_behind_it():
    """Sixteen scenes, sixteen frames: the photographer never stayed."""
    rows = [shot(f"s{i}", captured=at(i * 30)) for i in range(16)]
    worked = tendency.dwell(rows)
    assert worked.per_scene == 1.0
    assert worked.walks_on is True


def test_working_the_scene_is_not_accused():
    rows = [shot(f"s{i}", captured=at((i // 4) * 30 + i % 4)) for i in range(16)]
    worked = tendency.dwell(rows)
    assert worked.per_scene == pytest.approx(4.0)
    assert worked.walks_on is False


def test_dwell_says_nothing_from_two_scenes():
    assert tendency.dwell([shot("a", captured=at(0)), shot("b", captured=at(60))]).walks_on is False


def test_an_undated_shot_is_its_own_scene_not_a_neighbours():
    """Folding a shot with no capture time into whatever sorted next to it
    would invent a worked scene out of two unrelated frames."""
    rows = [shot("a", captured=at(0)), shot("b", captured=at(1)), shot("c")]
    assert tendency.dwell(rows).scenes == 2


# --- movement -------------------------------------------------------------------


def test_a_dimension_that_widened_is_reported_widest_first():
    before = tendency.build(corpus(10, subject=(0.5, 0.5)))
    after = tendency.build(
        corpus(10, subject=(0.5, 0.5)) + [shot(f"n{i}", subject=(0.1, 0.5)) for i in range(5)]
    )
    moved = tendency.diff(before, after)
    assert moved and moved[0].dimension.id == "placement"
    assert moved[0].widened is True
    assert moved[0].newly_used == ("near the edge",)


def test_nothing_moved_is_a_real_answer():
    before = tendency.build(corpus(10, subject=(0.5, 0.5)))
    after = tendency.build(corpus(12, subject=(0.5, 0.5)))
    assert tendency.diff(before, after) == []


# --- from a tendency to something to do -----------------------------------------


def test_every_suggested_technique_is_in_the_catalogue():
    """A rename in the taxonomy must not rot the bridge silently."""
    from app.domain import taxonomy

    suggested = {t for ids in tendency.PUSHES_AGAINST.values() for t in ids}
    suggested |= set(tendency.DWELL_SUGGESTS)
    assert suggested <= set(taxonomy.BY_ID)


def test_every_dominant_bucket_can_be_pushed_against():
    for dim in tendency.DIMENSIONS:
        for bucket in dim.buckets:
            assert (dim.id, bucket) in tendency.PUSHES_AGAINST, f"{dim.id}/{bucket}"


def test_walking_on_beats_every_other_tendency():
    """Sixteen scenes for sixteen shots is the loudest thing the profile can
    see, and the cheapest thing to change."""
    rows = [shot(f"s{i}", subject=(0.5, 0.5), captured=at(i * 30)) for i in range(16)]
    challenge = tendency.challenge_for(tendency.build(rows))
    assert challenge is not None and challenge.source == "dwell"
    assert "1.0 frames before you move on" in challenge.citation


def test_a_challenge_cites_the_count_that_earned_it():
    rows = [shot(f"s{i}", subject=(0.5, 0.5), captured=at(i)) for i in range(10)]
    challenge = tendency.challenge_for(tendency.build(rows))
    assert challenge is not None and challenge.source == "placement"
    assert "10 of 10 readable shots: centred" in challenge.citation
    assert "never off centre, near the edge" in challenge.citation
    assert "rule_of_thirds" in challenge.prefers


def test_a_photographer_with_no_tendency_is_told_nothing():
    """Inventing one to fill a card is the generic advice this refuses to give.
    Every readable dimension here is spread, including the one that catches
    most corpora out: they turned the camera."""
    points = [(0.5, 0.5), (0.35, 0.42), (0.1, 0.5)]
    sizes = [(800, 600), (600, 800), (700, 700)]
    rows = [
        shot(
            f"s{i}",
            subject=points[i % 3],
            cells=[2, 8, 20][i % 3],
            luma=[40, 120, 200][i % 3],
            warm=[30, 20, 5][i % 3],
            cool=[5, 18, 30][i % 3],
            size=sizes[i % 3],
            captured=at(i),
        )
        for i in range(12)
    ]
    profile = tendency.build(rows)
    assert profile.dwell.walks_on is False
    assert tendency.challenge_for(profile) is None


# --- the profile reorders the curriculum; it never widens it --------------------


def test_a_preference_reorders_what_the_curriculum_already_allows():
    from app.domain import scout as rules

    skills = {}
    plain = rules.choose(skills, [])
    assert plain is not None
    other = next(t for t in rules.rank(skills, []) if t.id != plain.id)
    assert rules.choose(skills, [], prefer=(other.id,)).id == other.id


def test_a_preference_cannot_unlock_a_technique_the_photographer_is_not_ready_for():
    """The curriculum decides what is possible; the profile only decides what
    is interesting among those. A locked technique stays locked however loudly
    the tendency asks for it."""
    from app.domain import scout as rules
    from app.domain import taxonomy

    skills = {}
    open_now = {t.id for t in rules.rank(skills, [])}
    locked = next(t for t in taxonomy.TECHNIQUES if t.id not in open_now)
    assert rules.choose(skills, [], prefer=(locked.id,)).id != locked.id
