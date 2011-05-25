# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

This module defines the classes for all types of boxes in the CSS formatting
structure / box model.

http://www.w3.org/TR/CSS21/visuren.html

Names are the same as in CSS 2.1 with the exception of TextBox. In WeasyPrint,
any text is in a TextBox.What CSS calls anonymous inline boxes are text boxes
but not all text boxes are anonymous inline boxes.

http://www.w3.org/TR/CSS21/visuren.html#anonymous

Abstract classes, should not be instanciated:

 * Box
 * BlockLevelBox
 * InlineLevelBox
 * BlockContainerBox
 * AnonymousBox
 * ReplacedBox

Concrete classes:

 * BlockBox
 * AnonymousBlockBox
 * InlineBox
 * InlineBlockBox
 * BlockLevelReplacedBox
 * InlineLevelReplacedBox
 * TextBox
 * LineBox

Apart from LineBox, all concrete box classes have one of the following "outside"
behavior:

 * Block-level (inherits from BlockLevelBox)
 * Inline-level (inherits from InlineLevelBox)

and one of the following "inside" behavior:

 * Block container (inherits from BlockContainerBox)
 * Inline content (is or inherits from InlineBox)
 * Replaced content (inherits from ReplacedBox)

See respective docstrings for details.

"""


import re
from . import css


class Box(object):
    """
    Abstract base class for all boxes.
    """
    def __init__(self, element):
        # Should never be None
        self.element = element
        # No parent yet. Will be set when this box is added to another box’s
        # children. Only the root box should stay without a parent.
        self.parent = None
        self.children = []
        self._init_style()
    
    def _init_style(self):
        # Computed values
        # Copying might not be needed, but let’s be careful with mutable
        # objects.
        self.style = self.element.style.copy()
    
    def add_child(self, child, index=None):
        """
        Add the new child to this box’s children list and set this box as the
        child’s parent.
        """
        child.parent = self
        if index == None:
            self.children.append(child)
        else:
            self.children.insert(index, child)
    
    def descendants(self):
        """A flat generator for a box, its children and descendants."""
        yield self
        for child in self.children or []:
            for grand_child in child.descendants():
                yield grand_child

    def ancestors(self):
        """Yield parent and recursively yield parent's parents."""
        parent = self
        while parent.parent:
            parent = parent.parent
            yield parent

    @property
    def index(self):
        """Index of the box in its parent's children."""
        if self.parent:
            return self.parent.children.index(self)


class BlockLevelBox(Box):
    """
    A box that participates in an block formatting context.

    An element with a 'display' value of 'block', 'liste-item' or 'table'
    generates a block-level box.
    """


class BlockContainerBox(Box):
    """
    A box that either contains only block-level boxes or establishes an inline
    formatting context and thus contains only line boxes.

    A non-replaced element with a 'display' value of 'block', 'list-item',
    'inline-block' or 'table-cell' generates a block container box.
    """


class BlockBox(BlockContainerBox, BlockLevelBox):
    """
    A block-level box that is also a block container.
    
    A non-replaced element with a 'display' value of 'block', 'list-item'
    generates a block box.
    """


class AnonymousBox(Box):
    """
    A box that is not directly generated by an element. Inherits style instead
    of copying them.
    """
    def _init_style(self):
        pseudo = css.PseudoElement(self.element, 'anonymous_box')
        # New PseudoElement has an empty .applicable_properties list:
        # no cascaded value, only inherited and initial values.
        # TODO: Maybe pre-compute initial values and remove the compute_values
        # step here.
        css.assign_properties(pseudo)
        self.style = pseudo.style


class AnonymousBlockBox(AnonymousBox, BlockBox):
    """
    Wraps inline-level boxes where block-level boxes are needed.
    
    Block containers (eventually) contain either only block-level boxes or only
    inline-level boxes. When they initially contain both, consecutive
    inline-level boxes are wrapped in an anonymous block box by 
    ``boxes.inline_in_block()``.
    """


class LineBox(AnonymousBox):
    """
    Eventually a line in an inline formatting context. Can only contain
    inline-level boxes.
    
    In early stages of building the box tree a single line box contains many
    consecutive inline boxes and will be split later when wrapping lines.
    """


class InlineLevelBox(Box):
    """
    A box that participates in an inline formatting context.
    
    An inline-level box that is not an inline box (see below) is said to be
    "atomic". Such boxes are inline-blocks, replaced elements and inline tables.

    An element with a 'display' value of 'inline', 'inline-table', or
    'inline-block' generates an inline-level box.
    """


class InlineBox(InlineLevelBox):
    """
    A box who participates in an inline formatting context and whose content
    also participates in that inline formatting context.
    
    A non-replaced element with a 'display' value of 'inline' generates an
    inline box.
    """


class TextBox(AnonymousBox, InlineBox):
    """
    A box that contains only text and has no box children.
    
    Any text in the document ends up in a text box. What CSS calls "anonymous
    inline boxes" are also text boxes.
    """
    def __init__(self, element, text):
        super(TextBox, self).__init__(element)
        self.children = None
        self.text = text


class InlineBlockBox(InlineLevelBox, BlockContainerBox):
    """
    A box that is both inline-level and a block container: it behaves as
    inline on the outside and as a block on the inside.

    A non-replaced element with a 'display' value of 'inline-block' generates an
    inline-block box.
    """


class ReplacedBox(Box):
    """
    A box that is replaced, ie. its content is rendered externally and is opaque
    from CSS’s point of view. Example: <img> elements are replaced.
    """


class BlockLevelReplacedBox(ReplacedBox, BlockLevelBox):
    """
    A box that is both replaced and block-level.

    A replaced element with a 'display' value of 'block', 'liste-item' or
    'table' generates a block-level replaced box.
    """


class InlineLevelReplacedBox(ReplacedBox, InlineLevelBox):
    """
    A box that is both replaced and inline-level.

    A replaced element with a 'display' value of 'inline', 'inline-table', or
    'inline-block' generates an inline-level replaced box.
    """


def dom_to_box(element):
    """
    Converts a DOM element (and its children) into a box (with children).
    
    Eg.
    
        <p>Some <em>emphasised</em> text.<p>
    
    gives (not actual syntax)
    
        BlockBox[
            TextBox('Some '),
            InlineBox[
                TextBox('emphasised'),
            ],
            TextBox(' text.'),
        ]
    
    TextBox`es are anonymous inline boxes:
    http://www.w3.org/TR/CSS21/visuren.html#anonymous
    """
    display = element.style.display # TODO: should be the used value
    assert display != 'none'
    
    if display in ('block', 'list-item'):
        box = BlockBox(element)
        #if display == 'list-item':
        #    TODO: add a box for the marker
    elif display == 'inline':
        box = InlineBox(element)
    elif display == 'inline-block':
        box = InlineBlockBox(element)
    else:
        raise NotImplementedError('Unsupported display: ' + display)
    
    if element.text:
        box.add_child(TextBox(element, element.text))
    for child_element in element:
        if child_element.style.display != 'none':
            box.add_child(dom_to_box(child_element))
        if child_element.tail:
            box.add_child(TextBox(element, child_element.tail))
    
    return box


def process_whitespace(box):
    """
    First part of "The 'white-space' processing model"
    http://www.w3.org/TR/CSS21/text.html#white-space-model
    """
    following_collapsible_space = False
    for box in box.descendants():
        if not (hasattr(box, 'text') and box.text):
            continue
        
        text = box.text
        handling = box.style.white_space
            
        text = re.sub('[\t\r ]*\n[\t\r ]*', '\n', text)
        if handling in ('pre', 'pre-wrap'):
            # \xA0 is the non-breaking space
            text = text.replace(' ', u'\xA0')
            if handling == 'pre-wrap':
                # "a line break opportunity at the end of the sequence"
                # \u200B is the zero-width space, marks a line break opportunity.
                text = re.sub(u'\xA0([^\xA0]|$)', u'\xA0\u200B\\1', text)
        elif handling in ('normal', 'nowrap'):
            # TODO: this should be language-specific
            # Could also replace with a zero width space character (U+200B),
            # or no character
            # CSS3: http://www.w3.org/TR/css3-text/#line-break-transform
            text = text.replace('\n', ' ')
    
        if handling in ('normal', 'nowrap', 'pre-line'):
            text = text.replace('\t', ' ')
            text = re.sub(' +', ' ', text)
            if following_collapsible_space and text.startswith(' '):
                text = text[1:]
            following_collapsible_space = text.endswith(' ')
        else:
            following_collapsible_space = False
        
        box.text = text


def inline_in_block(box):
    """
    Consecutive inline-level boxes in a block container box are wrapped into a
    line box, itself wrapped into an anonymous block box.
    (This line box will be broken into multiple lines later.)
    
    The box tree is changed *in place*.
    
    This is the first case in
    http://www.w3.org/TR/CSS21/visuren.html#anonymous-block-level
    
    Eg.
    
        BlockBox[
            TextBox('Some '),
            InlineBox[TextBox('text')],
            BlockBox[
                TextBox('More text'),
            ]
        ]
    
    is turned into
    
        BlockBox[
            AnonymousBlockBox[
                LineBox[
                    TextBox('Some '),
                    InlineBox[TextBox('text')],
                ]
            ]
            BlockBox[
                LineBox[
                    TextBox('More text'),
                ]
            ]
        ]
    """
    for child_box in box.children or []:
        inline_in_block(child_box)

    if not isinstance(box, BlockContainerBox):
        return
    
    line_box = LineBox(box.element)
    children = box.children
    box.children = []
    for child_box in children:
        if isinstance(child_box, BlockLevelBox):
            if line_box.children:
                # Inlines are consecutive no more: add this line box
                # and create a new one.
                anonymous = AnonymousBlockBox(box.element)
                anonymous.add_child(line_box)
                box.add_child(anonymous)
                line_box = LineBox(box.element)
            box.add_child(child_box)
        elif isinstance(child_box, LineBox):
            # Merge the line box we just found with the new one we are making
            for child in child_box.children:
                line_box.add_child(child)
        else:
            line_box.add_child(child_box)
    if line_box.children:
        # There were inlines at the end
        if box.children:
            anonymous = AnonymousBlockBox(box.element)
            anonymous.add_child(line_box)
            box.add_child(anonymous)
        else:
            # Only inline-level children: one line box
            box.add_child(line_box)


def block_in_inline(box):
    """
    Inline boxes containing block-level boxes will be broken in two
    boxes on each side on consecutive block-level boxes, each side wrapped
    in an anonymous block-level box.

    This is the second case in
    http://www.w3.org/TR/CSS21/visuren.html#anonymous-block-level
    
    Eg.
    
        BlockBox[
            LineBox[
                InlineBox[
                    TextBox('Hello.'),
                ],
                InlineBox[
                    TextBox('Some '),
                    InlineBox[
                        TextBox('text')
                        BlockBox[LineBox[TextBox('More text')]],
                        BlockBox[LineBox[TextBox('More text again')]],
                    ],
                    BlockBox[LineBox[TextBox('And again.')]],
                ]
            ]
        ]
    
    is turned into

        BlockBox[
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                        TextBox('Hello.'),
                    ],
                    InlineBox[
                        TextBox('Some '),
                        InlineBox[TextBox('text')],
                    ]
                ]
            ],
            BlockBox[LineBox[TextBox('More text')]],
            BlockBox[LineBox[TextBox('More text again')]],
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                    ]
                ]
            ],
            BlockBox[LineBox[TextBox('And again.')]],
            AnonymousBlockBox[
                LineBox[
                    InlineBox[
                    ]
                ]
            ],
        ]
    """
    # TODO: when splitting inline boxes, mark which are starting, ending, or
    # in the middle of the orginial box (for drawing borders).
    for child_box in box.children or []:
        block_in_inline(child_box)

    if not (isinstance(box, BlockLevelBox) and box.parent
            and isinstance(box.parent, InlineBox)):
        return
    
    # Find all ancestry until a line box.
    inline_parents = []
    for parent in box.ancestors():
        inline_parents.append(parent)
        if not isinstance(parent, InlineBox):
            assert isinstance(parent, LineBox)
            parent_line_box = parent
            break
            
    # Add an anonymous block level box before the block box
    if isinstance(parent_line_box.parent, AnonymousBlockBox):
        previous_anonymous_box = parent_line_box.parent
    else:
        previous_anonymous_box = AnonymousBlockBox(
            parent_line_box.element)
        parent_line_box.parent.add_child(
            previous_anonymous_box, parent_line_box.index)
        parent_line_box.parent.children.remove(parent_line_box)
        previous_anonymous_box.add_child(parent_line_box)

    # Add an anonymous block level box after the block box
    next_anonymous_box = AnonymousBlockBox(parent_line_box.element)
    previous_anonymous_box.parent.add_child(
        next_anonymous_box, previous_anonymous_box.index + 1)

    # Recreate anonymous inline boxes clones from the split inline boxes
    clone_box = next_anonymous_box
    while inline_parents:
        parent = inline_parents.pop()
        next_clone_box = type(parent)(parent.element)
        clone_box.add_child(next_clone_box)
        clone_box = next_clone_box

    splitter_box = box
    for parent in box.ancestors():
        if parent == parent_line_box:
            break
            
        next_children = parent.children[splitter_box.index + 1:]
        parent.children = parent.children[:splitter_box.index + 1]

        for child in next_children:
            clone_box.add_child(child)

        splitter_box = parent
        clone_box = clone_box.parent
        
    # Put the block element before the next_anonymous_box
    box.parent.children.remove(box)
    previous_anonymous_box.parent.add_child(
        box, previous_anonymous_box.index + 1)


