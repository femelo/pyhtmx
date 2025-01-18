from __future__ import annotations
import sys
from types import TracebackType
from typing import Any, Optional, Union, Iterable, List, Dict
import re
import xml.etree.ElementTree as etree


PARENT_TAG: Optional[HTMLTag] = None


# Helper functions
def _get_text_content(kwargs: Dict[str, Any]) -> Optional[str]:
    """Extract text content from kwargs dictionary.

    Looks for text content under various common key names and returns the first
    non-None value found. Removes the key from kwargs after extracting.

    Args:
        kwargs: Dictionary of keyword arguments that may contain text content

    Returns:
        Optional[str]: The text content if found, None otherwise
    """
    values = []
    for key in (
        "text",
        "text_content",
        "inner_html",
        "textContent",
        "innerHtml",
    ):
        if key in kwargs:
            value = kwargs.pop(key)
            if value is not None:
                values.append(value)
    return values[0] if values else None


def _convert_value_type(
    value: Any,
) -> Union[str, Iterable[str], Dict[str, str]]:
    """Convert a value to a string, list of strings, or dictionary of strings.

    Args:
        value: The value to convert. Can be any type.

    Returns:
        Union[str, Iterable[str], Dict[str, str]]: The converted value.
            - For lists/tuples/sets: Returns list of string representations
            - For dicts: Returns dict with string key/value pairs
            - For all other types: Returns string representation
    """
    if isinstance(value, (list, tuple, set)):
        _value = list(map(str, value))
    elif isinstance(value, dict):
        _value = dict(
            map(lambda k, v: (str(k), str(v)), value.keys(), value.values())
        )
    else:
        _value = str(value)
    return _value


def _format_value(value: Union[str, Iterable[str], Dict[str, str]]) -> str:
    """Convert a formatted value to a string representation.

    Args:
        value: The pre-formatted value to convert. Can be a string, iterable
            of strings, or dictionary of strings.

    Returns:
        str: The string representation of the value.
            - For lists/tuples/sets: Space-joined string of values (class list)
            - For dicts: CSS style format "key: value;" joined with spaces
            - For strings: The original string value
    """
    # Transform lists, dictionaries and other types in a string
    if isinstance(value, (list, tuple, set)):
        # for a class list
        _value = ' '.join(value)
    elif isinstance(value, dict):
        # for inline style
        _value = ' '.join(
            map(
                lambda k, v: f"{k}: {v};",
                value.keys(),
                value.values(),
            )
        )
    else:
        _value = str(value)  # copy value
    return _value


def _format_values(kwargs: Dict[str, Any]) -> Dict[str, str]:
    """Format dictionary values for HTML tag attributes.

    Takes a dictionary of attribute key/value pairs and formats all values
    into proper string representations using _format_value().

    Args:
        kwargs: Dictionary of attribute key/value pairs to format

    Returns:
        Dict[str, str]: Dictionary with same keys but values converted to
            strings using appropriate formatting rules:
            - Lists/sets become space-separated class lists
            - Dicts become CSS style strings
            - Other values converted to simple strings
    """
    return {key: _format_value(value) for key, value in kwargs.items()}


def _split_value(key: str, value: str) -> Union[str, List[str], Dict[str, str]]:
    """
    Splits the input value based on the provided key.

    Args:
        key (str): The key indicating how to split the value.
            Expected values are "class" or "style".
        value (str): The string value to be split.

    Returns:
        Union[str, List[str], Dict[str, str]]:
            - If key is "class", returns a list of class names.
            - If key is "style", returns a dictionary of style properties.
            - Otherwise, returns the original value.
    """
    if key == "class" and isinstance(value, str):
        split_value: List[str] = list(map(str.strip, value.split()))
    elif key == "style" and isinstance(value, str):
        pairs = map(str.strip, filter(lambda pair: pair != '', value.split(";")))
        split_value: Dict[str, str] = dict(
            map(lambda item: tuple(map(str.strip, item.split(":"))), pairs)
        )
    else:
        split_value: Union[str, List[str], Dict[str, str]] = value
    return split_value


def _preformat(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Preformat keyword arguments for HTML tag attributes.

    Processes kwargs dictionary to standardize attribute names and values:
    - Converts keys to lowercase
    - Handles special HTMX attributes with colons (hx:*, sse:*, ws:*)
    - Converts underscores to hyphens for HTMX attributes
    - Remove underscores for Python reserved words
    - Filters out empty/duplicate underscores
    - Converts values to appropriate string formats

    Args:
        kwargs: Dictionary of raw keyword arguments

    Returns:
        Dict[str, Any]: Dictionary with processed keys and formatted values
    """
    new_kwargs = {}
    for key, value in kwargs.items():
        _key = key.lower()
        # Usual keywords
        if '_' not in _key:
            new_kwargs[_key] = _split_value(_key, value)
            continue
        # HTMX keywords
        if any([_key.startswith(k) for k in ("hx", "sse", "ws")]):
            _key = re.sub(r"\_+colon\_+", ':', _key)
            delimiter = '-'
        else:
            # Other keywords (Python reserved words)
            delimiter = "_"
        # Filter out double, leading or trailing underscores
        new_key = delimiter.join(
            filter(lambda x: x != '', _key.split('_'))
        )
        new_kwargs[new_key] = _convert_value_type(_split_value(new_key, value))
    return new_kwargs


class HTMLTag:
    """
    Represents an HTML tag with its attributes and content.

    This class is used to create and manipulate HTML tags in a Pythonic way.
    It allows for easy creation of HTML elements with attributes and content,
    including text content and nested HTML tags.
    """
    def __init__(
        self: HTMLTag,
        tag: str,
        inner_content: Optional[
            Union[str, HTMLTag, List[Union[str, HTMLTag]]]
        ] = None,
        **kwargs: Any,
    ):
        self.tag = tag
        # Get text content and children, when available
        text_content: Optional[str] = None
        if inner_content is None:
            self._children = []
        elif isinstance(inner_content, str):
            text_content = inner_content
            self._children = []
        elif isinstance(inner_content, HTMLTag):
            self._children = [inner_content]
        else:
            self._children = list(
                map(
                    lambda child: HTMLTag("span", child)
                    if isinstance(child, str) else child,
                    inner_content,
                ),
            )
        # Check whether text content was specified with keyword argument
        kw_text_content = _get_text_content(kwargs)
        text_content = text_content or kw_text_content
        # Other attributes
        self.attributes: Dict[
            str, Union[str, Iterable[str], Dict[str, str]]
        ] = _preformat(kwargs)
        self._parent: Optional[HTMLTag] = None
        self._level: int = 0
        self._element: Optional[etree.Element] = None
        # Build element
        self._build_element(text=text_content)
        self._set_parent()

    @property
    def parent(self: HTMLTag) -> Optional[HTMLTag]:
        return self._parent

    @parent.setter
    def parent(self: HTMLTag, value: Optional[HTMLTag]) -> None:
        if value is None:
            if self._parent is not None and self._parent._element is not None:
                self._parent._element.remove(self._element)
            self._parent = value
        else:
            self._parent = value
            if self._parent is not None and self._parent._element is not None:
                self._parent._element.append(self._element)

    @property
    def children(self: HTMLTag) -> List[Union[str, HTMLTag]]:
        return self._children

    def update_attributes(
        self: HTMLTag,
        text_content: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        incremental: bool = False,
    ) -> None:
        if text_content or text_content == '':
            self._element.text = text_content
        if attributes:
            for key, value in _preformat(attributes).items():
                if isinstance(value, list):
                    if not incremental or key not in self.attributes:
                        self.attributes[key] = []
                    self.attributes[key].extend(
                        filter(lambda v: v not in self.attributes[key], value)
                    )
                elif isinstance(value, dict):
                    if not incremental or key not in self.attributes:
                        self.attributes[key] = {}
                    self.attributes[key].update(value)
                else:
                    self.attributes[key] = value
                # Apply new value
                self._element.set(key, _format_value(self.attributes[key]))

    def pop_child(
        self: HTMLTag,
        index: Optional[int] = None
    ) -> Optional[HTMLTag]:
        child: Optional[HTMLTag] = None
        # Pop child
        if not self._children:
            pass
        elif index is None:
            child = self._children.pop()
        elif 0 <= index < len(self._children):
            child = self._children.pop(index)
        else:
            pass
        # Detach child
        if child:
            child.parent = None
            child.level = 0
        return child

    def detach_children(self: HTMLTag) -> List[HTMLTag]:
        children = []
        while self._children:
            child = self._children.pop(0)
            child.parent = None
            child.level = 0
            children.append(child)
        return children

    def insert_child(self: HTMLTag, index: int, child: HTMLTag) -> None:
        if 0 <= index <= len(self._children):
            self._children.insert(index, child)
            child._parent = self
            if self._element is not None:
                self._element.insert(index, child._element)
            child.level = self.level + 1
        else:
            raise IndexError("Index out of range.")

    def add_child(self: HTMLTag, child: HTMLTag) -> None:
        self._children.append(child)
        child.parent = self
        child.level = self.level + 1

    def find_elements_by_tag(self: HTMLTag, tag: str) -> List[HTMLTag]:
        elements: List[HTMLTag] = []
        if self.tag == tag:
            elements.append(self)
        for child in self._children:
            elements += child.find_elements_by_tag(tag)
        return elements

    def find_element_by_id(self: HTMLTag, _id: str) -> Optional[HTMLTag]:
        if self.attributes.get("id") == _id:
            return self
        for child in self._children:
            element = child.find_element_by_id(_id)
            if element is not None:
                return element
        return None

    @property
    def level(self: HTMLTag) -> int:
        return self._level

    @level.setter
    def level(self: HTMLTag, value: int) -> None:
        self._level = value

    @property
    def tree(self: HTMLTag) -> etree.ElementTree:
        return etree.ElementTree(self._element)

    @property
    def text(self: HTMLTag) -> Optional[str]:
        return self._element.text

    @text.setter
    def text(self: HTMLTag, value: Optional[str]) -> None:
        self._element.text = value

    def _build_element(self: HTMLTag, text: Optional[str] = None) -> None:
        self._element = etree.Element(
            self.tag,
            attrib=_format_values(self.attributes)
        )
        if text is not None:
            self._element.text = text

    def _set_parent(self: HTMLTag) -> None:
        for child in self._children:
            child.parent = self
            child.level = self.level + 1

    def __enter__(self: HTMLTag) -> HTMLTag:
        global PARENT_TAG
        if PARENT_TAG is not None:
            PARENT_TAG.add_child(self)
        PARENT_TAG = self
        return self

    def __exit__(
        self: HTMLTag,
        typ: Optional[type] = None,
        value: Optional[Exception] = None,
        traceback: Optional[TracebackType] = None,
    ) -> None:
        global PARENT_TAG
        if PARENT_TAG is self:
            PARENT_TAG = self.parent

    def to_string(
        self: HTMLTag,
        space: str = 2 * " ",
        level: Optional[int] = None,
    ) -> str:
        if level is None:
            level = self.level
        etree.indent(self._element, space=space, level=level)
        if level == 0 and self.tag == "html":
            prefix = b"<!DOCTYPE html>\n"
        else:
            prefix = b''
        prefix += (level * space).encode()
        suffix = b'' if level > 0 else b'\n'
        encoded_string = prefix + \
            etree.tostring(self._element, method="html") + suffix
        return encoded_string.decode()

    def write(
        self: HTMLTag,
        filename: str,
        space: str = 2 * " ",
        level: Optional[int] = None,
    ) -> None:
        with open(filename, 'w') as file:
            file.write(
                self.to_string(
                    space=space,
                    level=level,
                )
            )

    def dump(
        self: HTMLTag, space:
        str = 2 * " ",
        level: Optional[int] = None,
    ) -> None:
        if level is None:
            level = self.level
        etree.indent(self._element, space=space, level=level)
        if level > 0:
            sys.stdout.write(level * space)
        etree.dump(self._element)
