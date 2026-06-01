# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024, Ansible Project

"""
Test rst_utils module.
"""

from __future__ import annotations

import pytest
from docutils import __version__ as docutils_version_string
from docutils import nodes
from docutils.parsers.rst import Directive

from antsibull_docutils.rst_code_finder import (
    CodeBlockInfo,
    _find_col_offset,
    _find_in_code,
    _find_indent,
    _find_offset,
    find_code_blocks,
    mark_antsibull_code_block,
)

DOCUTILS_VERSION = tuple(
    int(part) for part in docutils_version_string.split(".", 2)[:2]
)

FIND_CODE_BLOCKS: list[tuple[str, list[CodeBlockInfo]]] = [
    (
        r"""
Hello
=====

.. code-block::

  Foo
  Bar


.. code-block:: python



      Foo
        
    Bar

.. code-block::    foo  

Test

.. parsed-literal::

   # Escaped emphasis
   $ find \*foo\*

   # Not escaped emphasis
   $ find *foo*

.. does-not-exist::

""".lstrip(),
        [
            CodeBlockInfo(
                language=None,
                row_offset=5,
                col_offset=2,
                position_exact=True,
                directly_replacable_in_content=True,
                content="Foo\nBar\n",
                attributes={},
            ),
            CodeBlockInfo(
                language="python",
                row_offset=13,
                col_offset=4,
                position_exact=True,
                directly_replacable_in_content=True,
                content="  Foo\n\nBar\n",
                attributes={},
            ),
            CodeBlockInfo(
                language="foo",
                row_offset=19,
                col_offset=0,
                position_exact=False,
                directly_replacable_in_content=False,
                content="\n",
                attributes={},
            ),
        ],
    ),
    (
        r"""
+--------------------+-------------------------------+
| .. code-block::    | This is a test.               |
|                    |                               |
|    foo             | .. sourcecode:: python        |
|                    |                               |
|      bar           |    def foo(bar):              |
|                    |        return bar + 1         |
| Test               |                               |
|                    | More test!                    |
|      baz           |                               |
+--------------------+ * List item 1                 |
|                    | * List item 2 has some code   |
| Foo::              |                               |
|                    |   .. code::    c++            |
|   Bar!             |    :caption: Some test        |
|                    |                               |
| ::                 |    template<typename T>       |
|                    |    std::vector<T> create()    |
|   Baz              |    { return {}; }             |
+--------------------+-------------------------------+
| .. code:: foo      | .. code:: bar                 |
|                    |                               |
|   foo              |                               |
|                    |      foo                      |
|     !bar           |                               |
|                    |        !bar                   |
+--------------------+-------------------------------+

1. Test
2. Here is another table:

   +------------------------------+
   | .. code::                    |
   |                              |
   |   A test                     |
   +------------------------------+
   | .. code::                    |
   |    :caption: bla             |
   |                              |
   |    Another test              |
   +------------------------------+

3. Here is a CSV table:

   .. csv-table::
     :header: "Foo", "Bar"

     "A ""cell""!", ".. code::

       foo
       bar 1!"
     "Another cell", "A final one"

4. And here's a list table:

   .. list-table::
     :header-rows: 1

     * - Foo
       - Bar
     * - A "cell"!
       - .. code::

           foo
           bar 2!
     * - Another cell
       - A final one
""".lstrip(),
        [
            CodeBlockInfo(
                language=None,
                row_offset=3,
                col_offset=5,
                position_exact=True,
                directly_replacable_in_content=False,
                content="foo\n\n  bar\n",
                attributes={},
            ),
            CodeBlockInfo(
                language="python",
                row_offset=5,
                col_offset=26,
                position_exact=True,
                directly_replacable_in_content=False,
                content="def foo(bar):\n    return bar + 1\n",
                attributes={},
            ),
            CodeBlockInfo(
                language="c++",
                row_offset=16,
                col_offset=26,
                position_exact=True,
                directly_replacable_in_content=False,
                content="template<typename T>\nstd::vector<T> create()\n{ return {}; }\n",
                attributes={},
            ),
            (
                CodeBlockInfo(
                    language="foo",
                    row_offset=22,
                    col_offset=4,
                    position_exact=True,
                    directly_replacable_in_content=False,
                    content="foo\n\n  !bar\n",
                    attributes={},
                )
                if DOCUTILS_VERSION >= (0, 23)
                else CodeBlockInfo(
                    language="foo",
                    row_offset=23,
                    col_offset=0,
                    position_exact=False,
                    directly_replacable_in_content=False,
                    content="foo\n\n  !bar\n",
                    attributes={},
                )
            ),
            (
                CodeBlockInfo(
                    language="bar",
                    row_offset=23,
                    col_offset=0,
                    position_exact=False,
                    directly_replacable_in_content=False,
                    content="foo\n\n  !bar\n",
                    attributes={},
                )
                if DOCUTILS_VERSION >= (0, 23)
                else CodeBlockInfo(
                    language="bar",
                    row_offset=24,
                    col_offset=0,
                    position_exact=False,
                    directly_replacable_in_content=False,
                    content="foo\n\n  !bar\n",
                    attributes={},
                )
            ),
            CodeBlockInfo(
                language=None,
                row_offset=34,
                col_offset=7,
                position_exact=True,
                directly_replacable_in_content=False,
                content="A test\n",
                attributes={},
            ),
            CodeBlockInfo(
                language=None,
                row_offset=39,
                col_offset=8,
                position_exact=True,
                directly_replacable_in_content=False,
                content="Another test\n",
                attributes={},
            ),
            (
                CodeBlockInfo(
                    language=None,
                    row_offset=48,
                    col_offset=7,
                    position_exact=False,
                    directly_replacable_in_content=False,
                    content="foo\nbar 1!\n",
                    attributes={},
                )
                if DOCUTILS_VERSION >= (0, 23)
                else CodeBlockInfo(
                    language=None,
                    row_offset=49,
                    col_offset=7,
                    position_exact=True,
                    directly_replacable_in_content=False,
                    content="foo\nbar 1!\n",
                    attributes={},
                )
            ),
            CodeBlockInfo(
                language=None,
                row_offset=63,
                col_offset=11,
                position_exact=True,
                directly_replacable_in_content=True,
                content="foo\nbar 2!\n",
                attributes={},
            ),
        ],
    ),
]


@pytest.mark.parametrize("source, expected_code_block_infos", FIND_CODE_BLOCKS)
def test_find_code_blocks(
    source: str, expected_code_block_infos: list[CodeBlockInfo]
) -> None:
    found_code_block_infos = list(find_code_blocks(source))
    assert found_code_block_infos == expected_code_block_infos


class CodeBlockTest(Directive):
    def run(self) -> list[nodes.literal_block]:
        literal = nodes.literal_block("", "")
        mark_antsibull_code_block(
            literal,
            language="baz",
            line=self.lineno,
            other={"bar": "bam"},
        )
        return [literal]


def test_find_code_blocks_ext():
    source = """
.. foo::

Test::

  bar

Foo

::

  bazbam

.. code-block::

  foobar

Some invalid `markup <foo>

.. highlight:: python

::

  def foo():
    pass

.. literalinclude:: nox.py

| a
| b
  c
"""
    found_warnings = []
    found_warnings_2 = []

    def add_warning(line: int | str, col: int, message: str) -> None:
        found_warnings.append((line, col, message))

    def add_warning_2(
        line: int | str, col: int, message: str, unknown_origin: bool
    ) -> None:
        found_warnings_2.append((line, col, message, unknown_origin))

    found_code_block_infos = list(
        find_code_blocks(
            source,
            extra_directives={"foo": CodeBlockTest},
            warn_unknown_block=add_warning,
            warn_unknown_block_w_unknown_info=add_warning_2,
        )
    )
    assert found_code_block_infos == [
        CodeBlockInfo(
            language="baz",
            row_offset=3,
            col_offset=0,
            position_exact=False,
            directly_replacable_in_content=False,
            content="\n",
            attributes={
                "antsibull-other-bar": "bam",
            },
        ),
        CodeBlockInfo(
            language=None,
            row_offset=15,
            col_offset=2,
            position_exact=True,
            directly_replacable_in_content=True,
            content="foobar\n",
            attributes={},
        ),
    ]
    assert found_warnings == []
    assert found_warnings_2 == [
        (6, 0, "bar", False),
        (12, 0, "bazbam", False),
        (24, 0, "def foo():\n  pass", False),
    ]


def test__find_col_offset() -> None:
    document_content_lines = """
    foo       foo foo  foo
      bar       bar bar  bar foo
                               bar
    baz       baz baz  baz
""".lstrip("\n").splitlines()
    content = """
foo
  bar

baz
""".lstrip("\n")
    content_2 = """
foo
  bar
""".lstrip("\n")

    assert _find_col_offset(
        0, content, document_content_lines=document_content_lines
    ) == [4, 14, 23]
    assert _find_col_offset(
        0, content_2, document_content_lines=document_content_lines
    ) == [4, 14, 23]
    assert _find_col_offset(
        1, content_2, document_content_lines=document_content_lines
    ) == [29]
    assert _find_col_offset(
        1, "bar", document_content_lines=document_content_lines
    ) == [6, 16, 20, 25]
    assert _find_col_offset(
        2, "bar", document_content_lines=document_content_lines
    ) == [31]

    # Code block does not fit.
    assert (
        _find_col_offset(1, content, document_content_lines=document_content_lines)
        == []
    )

    # No first candidates
    assert (
        _find_col_offset(0, "bar", document_content_lines=document_content_lines) == []
    )
    assert (
        _find_col_offset(2, content, document_content_lines=document_content_lines)
        == []
    )


FIND_INDENT: list[tuple[str, int | None]] = [
    (
        r"""
        """,
        None,
    ),
    (
        r"""
        x
        """,
        8,
    ),
    (
        r"""
Foo
        """,
        0,
    ),
    (
        r"""        Foo

   Bar""",
        3,
    ),
]


@pytest.mark.parametrize("source, expected_indent", FIND_INDENT)
def test__find_indent(source: str, expected_indent: int | None) -> None:
    indent = _find_indent(source)
    assert indent == expected_indent


FIND_OFFSET: list[
    tuple[int | None, int | None, str, str | None, str, int, int, bool]
] = [
    (
        2,
        None,
        r"""Foo
 Bar
""",
        None,
        r"""
.. code-block::
    :foo: bar

    Foo
     Bar

Afterwards.
        """,
        4,
        4,
        True,
    ),
    (
        2,
        None,
        r"""Foo
 Bar
""",
        None,
        r"""
   .. code-block::
       :foo: bar

      Foo
       Bar

Afterwards.
        """,
        4,
        6,
        True,
    ),
    (
        2,
        None,
        r"""Foo
 Bar
""",
        None,
        r"""
+-----------------+
| .. code-block:: |
|    :foo: bar    |
|                 |
|     Foo         |
|      Bar        |
+-----------------+
        """,
        2,
        0,
        True,
    ),
    (
        2,
        None,
        r"""Foo

 Bar
""",
        None,
        r"""
+-----------------+
| .. code-block:: |
|    :foo: bar    |
|                 |
|     Foo         |
|                 |
|      Bar        |
+-----------------+
        """,
        2,
        0,
        True,
    ),
    (
        2,
        None,
        r"""Foo
 Bar
""",
        None,
        r"""
.. code-block::
        """,
        3,
        0,
        False,
    ),
]


@pytest.mark.parametrize(
    "lineno, content_offset, content, block_text, document_content, expected_line, expected_col, expected_position_exact",
    FIND_OFFSET,
)
def test__find_offset(
    lineno: int | None,
    content_offset: int | None,
    content: str,
    block_text: str | None,
    document_content: str,
    expected_line: int,
    expected_col: int,
    expected_position_exact: bool,
) -> None:
    line, col, position_exact = _find_offset(
        lineno,
        content_offset,
        content,
        block_text,
        document_content_lines=document_content.splitlines(),
    )
    print(line, col, position_exact)
    assert line == expected_line
    assert col == expected_col
    assert position_exact == expected_position_exact


FIND_IN_CODE: list[tuple[int, int, str, str, bool]] = [
    (
        4,
        3,
        r"""Foo
Bar""",
        r"""
.. code-block::
    :foo: bar

   Foo
   Bar

Afterwards.
        """,
        True,
    ),
    (
        4,
        3,
        r"""Foo

  Bar""",
        r"""
.. code-block::
    :foo: bar

   Foo
  
     Bar

Afterwards.
        """,
        True,
    ),
    (
        4,
        3,
        r"""Foo
Bar""",
        r"""
.. code-block::
    :foo: bar

   Foo
    Bar

Afterwards.
        """,
        False,
    ),
    (
        4,
        3,
        r"""Foo
Bar""",
        r"""
.. code-block::
    :foo: bar

   Foo""",
        False,
    ),
    (
        4,
        3,
        r"""Foo
Bar""",
        r"""
.. code-block::
    :foo: bar

   Foo
  Bar
""",
        False,
    ),
    (
        2,
        0,
        r"""Foo
 Bar
""",
        r"""
+-----------------+
| .. code-block:: |
|    :foo: bar    |
|                 |
|     Foo         |
|      Bar        |
+-----------------+
        """,
        False,
    ),
    (
        2,
        2,
        r"""Foo
 Bar
""",
        r"""
+-----------------+
| .. code-block:: |
|    :foo: bar    |
|                 |
|     Foo         |
|      Bar        |
+-----------------+
        """,
        False,
    ),
    (
        5,
        6,
        r"""Foo
 Bar
""",
        r"""
+-----------------+
| .. code-block:: |
|    :foo: bar    |
|                 |
|     Foo         |
|      Bar        |
+-----------------+
        """,
        False,
    ),
]


@pytest.mark.parametrize(
    "line, col, content, document_content, expected_easy_to_replace", FIND_IN_CODE
)
def test__find_in_code(
    line: int,
    col: int,
    content: str,
    document_content: str,
    expected_easy_to_replace: bool,
) -> None:
    easy_to_replace = _find_in_code(
        line, col, content, document_content_lines=document_content.splitlines()
    )
    assert easy_to_replace == expected_easy_to_replace
