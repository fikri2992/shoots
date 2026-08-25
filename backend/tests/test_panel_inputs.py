"""Decision 18's input half: each reader is left with its own frame.

The panel is a ParallelAgent under one user turn, so until the routing
callback existed every lens saw both images and the Synthesizer — documented
as never seeing the picture — saw two.
"""

from google.genai import types

from app.agents.analyst import SEES, only_image
from app.domain import panel

GRIDDED = b"gridded-frame-bytes"
CLEAN = b"clean-frame-bytes"


def turn() -> list[types.Content]:
    """What ``analyse`` sends: the prompt, then gridded, then clean."""
    return [
        types.Content(
            role="user",
            parts=[
                types.Part(text="read this shot"),
                types.Part.from_bytes(data=GRIDDED, mime_type="image/png"),
                types.Part.from_bytes(data=CLEAN, mime_type="image/jpeg"),
            ],
        )
    ]


def images_in(contents: list[types.Content]) -> list[bytes]:
    return [
        p.inline_data.data
        for c in contents
        for p in (c.parts or [])
        if getattr(p, "inline_data", None) is not None
    ]


def test_each_lens_keeps_only_its_own_frame():
    assert images_in(only_image(turn(), SEES[panel.TECHNICIAN])) == [GRIDDED]
    assert images_in(only_image(turn(), SEES[panel.COMPOSER])) == [GRIDDED]
    assert images_in(only_image(turn(), SEES[panel.STORYTELLER])) == [CLEAN]


def test_the_synthesizer_sees_no_picture_at_all():
    """It writes from the three readings. It never had a reason to look."""
    assert images_in(only_image(turn(), SEES["synthesizer"])) == []


def test_the_words_survive_the_filter():
    """Only images are routed; the prompt reaches every reader intact."""
    for keep in SEES.values():
        kept = only_image(turn(), keep)
        assert [p.text for c in kept for p in (c.parts or []) if p.text] == ["read this shot"]


def test_the_storyteller_never_sees_the_mesh():
    """The one that matters: asking how a picture feels while a grid is drawn
    over it is asking about a different picture."""
    assert GRIDDED not in images_in(only_image(turn(), SEES[panel.STORYTELLER]))


def test_every_panel_member_has_a_route():
    assert set(panel.PANEL) <= set(SEES)


def test_routing_does_not_mutate_the_original():
    original = turn()
    only_image(original, 1)
    assert images_in(original) == [GRIDDED, CLEAN]
