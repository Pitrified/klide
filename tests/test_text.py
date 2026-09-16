"""Wrapping, which is what phase 2 and 3 did not have."""

from klide.fonts import Face
from klide.text import Column, Style, measure, wrap

BODY = Style(face=Face.BODY, size_px=46)
MONO = Style(face=Face.MONO, size_px=40, preformatted=True)


def test_short_text_stays_on_one_line() -> None:
    assert wrap("a few words", BODY, 2000) == ["a few words"]


def test_wrapping_happens_by_measuring_not_by_counting_characters() -> None:
    # The body face is proportional, so a character count is wrong by a different amount on every
    # line. "iiiiiiiiii" and "mmmmmmmmmm" are the same length and nowhere near the same width.
    assert measure("iiiiiiiiii", BODY) < measure("mmmmmmmmmm", BODY)


def test_every_wrapped_line_fits() -> None:
    text = "the frame is the evidence and the simulator exists to produce it " * 4
    width = 600
    for line in wrap(text, BODY, width):
        assert measure(line, BODY) <= width


def test_a_word_longer_than_the_line_is_broken_rather_than_overflowing() -> None:
    # A long path or URL is the realistic case. Letting it overflow means silent clipping, which is
    # the failure this module exists to remove.
    lines = wrap("/very/long/path/that/cannot/possibly/fit/in/the/column", BODY, 200)
    assert len(lines) > 1
    for line in lines:
        assert measure(line, BODY) <= 200


def test_wrapping_loses_no_words() -> None:
    text = "one two three four five six seven eight nine ten eleven twelve"
    assert " ".join(wrap(text, BODY, 300)).split() == text.split()


def test_empty_text_produces_one_empty_line_rather_than_nothing() -> None:
    assert wrap("", BODY, 500) == [""]


def test_a_column_wraps_what_it_is_given() -> None:
    column = Column(width=400)
    column.add("a sentence long enough that it cannot fit on one line of this column", BODY)
    assert len(column.lines) > 1
    for line in column.lines:
        assert measure(line.text, BODY) <= 400


def test_preformatted_text_is_cut_rather_than_wrapped() -> None:
    # Folding a diff or a code line makes it look like two lines and lie about its structure.
    column = Column(width=300)
    column.add("    return some_function(with_a_very_long_argument_list, and_another)", MONO)
    assert len(column.lines) == 1
    assert column.lines[0].text.endswith("…")


def test_a_preformatted_line_that_fits_is_left_alone() -> None:
    column = Column(width=2000)
    column.add("    return x", MONO)
    assert column.lines[0].text == "    return x"


def test_preformatted_keeps_its_own_line_breaks() -> None:
    column = Column(width=2000)
    column.add("one\ntwo\nthree", MONO)
    assert [line.text for line in column.lines] == ["one", "two", "three"]


def test_indent_reduces_the_space_available() -> None:
    wide = Column(width=600)
    wide.add("the frame is the evidence and the simulator exists to produce it", BODY)
    narrow = Column(width=600)
    narrow.add("the frame is the evidence and the simulator exists to produce it", BODY, indent=300)
    assert len(narrow.lines) > len(wide.lines)
