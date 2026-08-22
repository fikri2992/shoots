from app.agents.scout import normalise_brief


def test_inline_steps_become_lines():
    text = "1. Head outside at golden hour. 2. Set f/1.8 to f/4. 3. Face the light."
    assert normalise_brief(text).split("\n") == [
        "1. Head outside at golden hour.",
        "2. Set f/1.8 to f/4.",
        "3. Face the light.",
    ]


def test_multiline_briefs_are_only_tidied():
    text = "1. One\n\n2. Two  spaced\n3. Three\n"
    assert normalise_brief(text) == "1. One\n2. Two spaced\n3. Three"


def test_decimals_inside_a_step_do_not_split():
    text = "1. Use f/1.8 or wider. 2. Keep ISO at 100."
    assert normalise_brief(text).count("\n") == 1
