"""What the overlay draws, checked on the pixels it produces."""

from PIL import Image

from app.domain.entities import Composition, GridSpec, Move, MoveKind
from app.imaging.overlay import render_overlay

SPEC = GridSpec(cols=8, rows=8, width=800, height=800)


def frame() -> Image.Image:
    return Image.new("RGB", (800, 800), (40, 90, 140))


def render(composition: Composition) -> Image.Image:
    return render_overlay(frame(), SPEC, composition)


def test_a_camera_change_puts_no_mark_on_the_frame():
    """ "Kneel to her eye level" is not a direction on a flat image."""
    bare = render(Composition(guide="none"))
    with_camera = render(
        Composition(
            guide="none",
            moves=[Move(what="kneel to her eye level", kind=MoveKind.CAMERA, reason="")],
        )
    )
    assert bare.tobytes() == with_camera.tobytes()


def test_a_crop_dims_what_leaves_and_leaves_the_keeper_alone():
    out = render(Composition(guide="none", suggested_crop_cells=["C3", "F6"]))
    inside = out.getpixel((400, 400))
    outside = out.getpixel((20, 20))
    assert sum(outside) < sum(inside)


def test_a_move_is_drawn_only_when_it_has_both_ends():
    half = Move(what="shift her", kind=MoveKind.MOVE, from_cells=["D4"])
    one_ended = render(Composition(guide="none", moves=[half]))
    assert one_ended.tobytes() == render(Composition(guide="none")).tobytes()


def test_the_guide_is_drawn_but_stays_quiet():
    """Thirds must be visible against the frame and far dimmer than a finding."""
    plain = frame()
    thirds = render(Composition(guide="thirds"))
    on_the_line = thirds.getpixel((267, 400))
    assert on_the_line != plain.getpixel((267, 400))

    subject = render(Composition(guide="none", subject_cells=["D4", "E5"]))
    subject_lift = _lift(subject.getpixel((300, 300)), plain.getpixel((300, 300)))
    assert subject_lift > _lift(on_the_line, plain.getpixel((267, 400)))


def test_the_subject_point_is_drawn_where_the_lens_put_it():
    out = render(Composition(guide="none", subject_x=0.25, subject_y=0.75))
    assert out.getpixel((200, 600)) != frame().getpixel((200, 600))


def test_selected_guide_layer_does_not_stack_the_available_crop():
    composition = Composition(
        guide="thirds",
        subject_x=0.5,
        subject_y=0.5,
        suggested_crop_cells=["C3", "F6"],
    )
    guide_only = render_overlay(frame(), SPEC, composition, layer="guide")
    action_only = render_overlay(frame(), SPEC, composition, layer="action")

    assert guide_only.getpixel((20, 20)) == frame().getpixel((20, 20))
    assert action_only.getpixel((20, 20)) != frame().getpixel((20, 20))
    assert guide_only.getpixel((267, 400)) != frame().getpixel((267, 400))


def _lift(pixel: tuple[int, int, int], base: tuple[int, int, int]) -> int:
    return sum(abs(a - b) for a, b in zip(pixel, base, strict=True))
