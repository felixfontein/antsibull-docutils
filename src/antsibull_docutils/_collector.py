# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Formatted text collecting utilities.
"""

from __future__ import annotations

import abc
import dataclasses
import enum
import typing as t
from collections import defaultdict

from ._string import StringProcessor

_T = t.TypeVar("_T")


class Formatting(enum.Enum):
    """
    Text formattings that can be set and unset.
    """

    BOLD = 1
    FAINT = 2
    ITALICS = 3
    UNDERLINE = 4
    STRIKE = 5


class State(t.Generic[_T], metaclass=abc.ABCMeta):
    """
    Represents formatting state used for collecting line-by-line formatted text.
    """

    @abc.abstractmethod
    def clone(self) -> State:
        """
        Create a clone of the current state object.
        """

    @abc.abstractmethod
    def push_formatting(self, formatting: Formatting) -> t.Self:
        """
        Add the given formatting to the state.
        A formatting can be added multiple times; this usually has no visible effect.
        """

    @abc.abstractmethod
    def pop_formatting(self, formatting: Formatting) -> t.Self:
        """
        Remove the given formatting once from the state.
        A formatting can be added multiple times; this usually has no visible effect.
        """

    @abc.abstractmethod
    def clear_formatting(self, formatting: Formatting) -> t.Self:
        """
        Remove the given formatting completely from the state.
        """

    @abc.abstractmethod
    def get_state(self) -> _T:
        """
        Return the current state.
        """

    @abc.abstractmethod
    def get_start_of_line(self, state: _T) -> str:
        """
        Get formatting string for the start of a line.
        """

    @abc.abstractmethod
    def get_end_of_line(self, state: _T) -> str:
        """
        Get formatting string for the end of a line.
        """

    @abc.abstractmethod
    def update_state(
        self, previous_state: _T, has_line_content: bool
    ) -> tuple[str, _T]:
        """
        Update the state.

        The parameter ``has_line_content`` indicates whether there
        already is some content in the currnet line.

        The return value is ``(format_string, state)``, where
        ``format_string`` is a string to insert into the current line
        and ``state`` is the new state.

        If ``has_line_content == True``, ``format_string`` is empty
        since it is assumed that ``get_start_of_line(state)`` will be
        added before any content is put into the line.
        """


class EmptyState(State[tuple[()]]):
    """
    An empty state.
    """

    def clone(self) -> EmptyState:
        """
        Create a clone of the current state object.
        """
        return self

    def push_formatting(self, formatting: Formatting) -> t.Self:
        """
        Add the given formatting to the state.
        A formatting can be added multiple times; this usually has no visible effect.
        """
        return self

    def pop_formatting(self, formatting: Formatting) -> t.Self:
        """
        Remove the given formatting once from the state.
        A formatting can be added multiple times; this usually has no visible effect.
        """
        return self

    def clear_formatting(self, formatting: Formatting) -> t.Self:
        """
        Remove the given formatting completely from the state.
        """
        return self

    def get_state(self) -> tuple[()]:
        """
        Return the current state.
        """
        return ()

    def get_start_of_line(self, state: tuple[()]) -> str:
        """
        Get formatting string for the start of a line.
        """
        return ""

    def get_end_of_line(self, state: tuple[()]) -> str:
        """
        Get formatting string for the end of a line.
        """
        return ""

    def update_state(
        self, previous_state: tuple[()], has_line_content: bool
    ) -> tuple[str, tuple[()]]:
        """
        Update the state.

        The parameter ``has_line_content`` indicates whether there
        already is some content in the currnet line.

        The return value is ``(format_string, state)``, where
        ``format_string`` is a string to insert into the current line
        and ``state`` is the new state.

        If ``has_line_content == True``, ``format_string`` is empty
        since it is assumed that ``get_start_of_line(state)`` will be
        added before any content is put into the line.
        """
        return "", ()


@dataclasses.dataclass(frozen=True)
class ANSIStateElt:
    """
    State element for ANSI formatting.
    """

    bold: bool
    faint: bool
    italics: bool
    underline: bool
    strike: bool

    def _get_seq(self) -> tuple[tuple[str, bool], ...]:
        return (
            ("1", self.bold),
            ("2", self.faint),
            ("3", self.italics),
            ("4", self.underline),
            ("9", self.strike),
        )

    def _get_clear(self) -> str:
        if any(f for _v, f in self._get_seq()):
            return "\033[0m"
        return ""

    def _get_set(self) -> str:
        parts = []
        for v, f in self._get_seq():
            if f:
                parts.append(v)
        if not parts:
            return ""
        return f"\033[0;{';'.join(parts)}m"

    def _get_diff_to(self, previous: ANSIStateElt) -> str:
        parts = []
        clear = False
        # pylint: disable-next=protected-access
        for (v, f), (_ov, of) in zip(self._get_seq(), previous._get_seq()):
            if f:
                parts.append(v)
            elif of:
                clear = True
        if not parts:
            return "\033[0m" if clear else ""
        return f"\033[0;{';'.join(parts)}m"


class ANSIState(State[ANSIStateElt]):
    """
    Uses ANSI formatting sequences.
    """

    def __init__(self) -> None:
        self._counters: defaultdict[Formatting, int] = defaultdict(lambda: 0)

    def push_formatting(self, formatting: Formatting) -> t.Self:
        """
        Add the given formatting to the state.
        A formatting can be added multiple times; this usually has no visible effect.
        """
        self._counters[formatting] = self._counters[formatting] + 1
        return self

    def pop_formatting(self, formatting: Formatting) -> t.Self:
        """
        Remove the given formatting once from the state.
        A formatting can be added multiple times; this usually has no visible effect.
        """
        self._counters[formatting] = max(0, self._counters[formatting] - 1)
        return self

    def clear_formatting(self, formatting: Formatting) -> t.Self:
        """
        Remove the given formatting completely from the state.
        """
        self._counters[formatting] = 0
        return self

    def clone(self) -> ANSIState:
        """
        Create a clone of the current state object.
        """
        result = ANSIState()
        # pylint: disable-next=protected-access
        result._counters.update(self._counters)
        return result

    def get_state(self) -> ANSIStateElt:
        """
        Return the current state.
        """
        return ANSIStateElt(
            bold=self._counters[Formatting.BOLD] > 0,
            faint=self._counters[Formatting.FAINT] > 0,
            italics=self._counters[Formatting.ITALICS] > 0,
            underline=self._counters[Formatting.UNDERLINE] > 0,
            strike=self._counters[Formatting.STRIKE] > 0,
        )

    def get_start_of_line(self, state: ANSIStateElt) -> str:
        """
        Get formatting string for the start of a line.
        """
        # pylint: disable-next=protected-access
        return state._get_set()

    def get_end_of_line(self, state: ANSIStateElt) -> str:
        """
        Get formatting string for the end of a line.
        """
        # pylint: disable-next=protected-access
        return state._get_clear()

    def update_state(
        self, previous_state: ANSIStateElt, has_line_content: bool
    ) -> tuple[str, ANSIStateElt]:
        """
        Update the state.

        The parameter ``has_line_content`` indicates whether there
        already is some content in the currnet line.

        The return value is ``(format_string, state)``, where
        ``format_string`` is a string to insert into the current line
        and ``state`` is the new state.

        If ``has_line_content == True``, ``format_string`` is empty
        since it is assumed that ``get_start_of_line(state)`` will be
        added before any content is put into the line.
        """
        new_state = self.get_state()
        if new_state == previous_state or not has_line_content:
            return "", new_state
        # pylint: disable-next=protected-access
        return new_state._get_diff_to(previous_state), new_state


class Collector:  # pylint: disable=too-many-instance-attributes
    """
    Collect text into formatted lines.
    """

    def __init__(
        self, *, width: int, state: State, string_proc: StringProcessor
    ) -> None:
        self.width = width
        self.state = state
        self.string_proc = string_proc
        self.lines: list[str] = []
        self.parts: list[str] = []
        self.current_line_columns = 0
        self.space = ""
        self.space_columns = 0
        self.insert_paragraph = False
        self.current_state = self.state.get_state()

    def _flush_line(self) -> None:
        if self.parts:
            if self.insert_paragraph and self.lines:
                self.lines.append("")
            self.parts.append(self.state.get_end_of_line(self.current_state))
            self.lines.append("".join(self.parts))
            self.parts.clear()
            self.insert_paragraph = False
        self.current_line_columns = 0
        self.space = ""
        self.space_columns = 0

    def append(self, *, text: str) -> None:
        """
        Append text.
        """
        while text:
            remaining = self.width - (self.current_line_columns + self.space_columns)
            newline, main, main_columns, space, space_columns, text = (
                self.string_proc.split(
                    text=text, remaining_columns=remaining, total_columns=self.width
                )
            )
            assert main != "" or space != ""
            if newline:
                self._flush_line()
            if self.space or main:
                if not self.parts:
                    self.parts.append(self.state.get_start_of_line(self.current_state))
                if self.space:
                    self.parts.append(self.space)
                    self.current_line_columns += self.space_columns
                if main:
                    self.parts.append(main)
            self.current_line_columns += main_columns
            if self.current_line_columns + space_columns >= self.width:
                self._flush_line()
            else:
                self.space = space
                self.space_columns = space_columns

    def update_state(self) -> None:
        """
        Update the state.

        Assumes that ``self.state`` might have been modified, and will insert
        appropriate formatting.
        """
        if self.space:
            if not self.parts:
                self.parts.append(self.state.get_start_of_line(self.current_state))
            self.parts.append(self.space)
            self.current_line_columns += self.space_columns
            self.space = ""
            self.space_columns = 0

        change, self.current_state = self.state.update_state(
            self.current_state, bool(self.parts)
        )
        if change:
            self.parts.append(change)

    def new_par(self) -> None:
        """
        Start a new paragraph.
        """
        self._flush_line()
        self.insert_paragraph = True

    def close(self) -> list[str]:
        """
        Close the collector and return the formatted lines of text.

        No further calls to collector methods must be done after calling this.
        """
        self._flush_line()
        return self.lines
