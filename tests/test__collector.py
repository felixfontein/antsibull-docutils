# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Test _collector module.
"""

from __future__ import annotations

import typing as t

import pytest

from antsibull_docutils._collector import (
    ANSIState,
    Collector,
    EmptyState,
    Formatting,
    State,
)
from antsibull_docutils._string import ASCIIStringProcessor

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

    InputElt = str | None | tuple[Formatting, t.Literal["push", "pop", "clear"]]


def process_input(
    input: Sequence[InputElt],
    state: State,
    collector: Collector,
) -> None:
    for part in input:
        if part is None:
            collector.new_par()
        elif isinstance(part, str):
            collector.append(text=part)
        else:
            formatting, op = part
            if op == "push":
                state.push_formatting(formatting)
            if op == "pop":
                state.pop_formatting(formatting)
            if op == "clear":
                state.clear_formatting(formatting)
            collector.update_state()


TEST_EMPTYSTATE_COLLECTOR_DATA: list[tuple[list[InputElt], int, list[str]]] = [
    (
        [],
        1,
        [],
    ),
    (
        ["Hello world! This is a text."],
        10,
        ["Hello", "world!", "This is a", "text."],
    ),
    (
        [
            "Hello world! This ",
            (Formatting.ITALICS, "push"),
            "is",
            (Formatting.ITALICS, "pop"),
            " a ",
            (Formatting.BOLD, "clear"),
            "text",
            (Formatting.BOLD, "push"),
            ".",
        ],
        10,
        ["Hello", "world!", "This is a", "text."],
    ),
    (
        ["Hello world! This is a text. bazbamfoo Foobarbazbam"],
        10,
        ["Hello", "world!", "This is a", "text.", "bazbamfoo", "Foobarbazb", "am"],
    ),
    (
        [
            "Hello world!",
            " ",
            "This",
            " is ",
            "a text.",
            None,
            "bazbamfoo",
            " ",
            "Foobarbazbam",
        ],
        10,
        ["Hello", "world!", "This is a", "text.", "", "bazbamfoo", "Foobarbazb", "am"],
    ),
]


@pytest.mark.parametrize(
    "input, width, expected_lines",
    TEST_EMPTYSTATE_COLLECTOR_DATA,
)
def test_EmptyState_Collector(
    input: list[InputElt],
    width: int,
    expected_lines: list[str],
) -> None:
    string_proc = ASCIIStringProcessor()
    state = EmptyState()
    assert state.clone() is state
    collector = Collector(width=width, state=state, string_proc=string_proc)
    process_input(input, state, collector)
    lines = collector.close()
    assert lines == expected_lines


TEST_ANSISTATE_COLLECTOR_DATA: list[tuple[list[InputElt], int, list[str]]] = [
    (
        [
            "Hello world! This ",
            (Formatting.ITALICS, "push"),
            "is",
            (Formatting.ITALICS, "pop"),
            " a ",
            (Formatting.BOLD, "push"),
            "text",
            (Formatting.BOLD, "pop"),
            ".",
        ],
        10,
        ["Hello", "world!", "This \033[0;3mis\033[0m a", "\033[0;1mtext\033[0m."],
    ),
    (
        [
            "Hello world! This ",
            (Formatting.ITALICS, "push"),
            "is",
            (Formatting.BOLD, "push"),
            " a ",
            (Formatting.BOLD, "push"),
            "text",
            (Formatting.BOLD, "pop"),
            ".",
            (Formatting.BOLD, "pop"),
            ".",
            (Formatting.ITALICS, "pop"),
            ".",
        ],
        10,
        [
            "Hello",
            "world!",
            "This \033[0;3mis\033[0;1;3m a\033[0m",
            "\033[0;1;3mtext.\033[0;3m.\033[0m.",
        ],
    ),
    (
        [
            "   ",
            (Formatting.ITALICS, "push"),
            "foo!",
            (Formatting.ITALICS, "pop"),
            " ",
            (Formatting.BOLD, "push"),
            "bar",
            (Formatting.BOLD, "pop"),
            " ",
        ],
        20,
        ["   \033[0;3mfoo!\033[0m \033[0;1mbar\033[0m"],
    ),
    (
        [
            (Formatting.ITALICS, "push"),
            (Formatting.ITALICS, "push"),
            (Formatting.ITALICS, "clear"),
            "x",
        ],
        1,
        ["x"],
    ),
    (
        [
            "foo  ",
            "  ",
            "bar",
        ],
        10,
        ["foo    bar"],
    ),
]


@pytest.mark.parametrize(
    "input, width, expected_lines",
    TEST_ANSISTATE_COLLECTOR_DATA,
)
def test_ANSIState_Collector(
    input: list[InputElt],
    width: int,
    expected_lines: list[str],
) -> None:
    string_proc = ASCIIStringProcessor()
    state = ANSIState()
    assert state.clone() is not state
    collector = Collector(width=width, state=state, string_proc=string_proc)
    process_input(input, state, collector)
    lines = collector.close()
    for line in lines:
        print(line)
    assert lines == expected_lines
