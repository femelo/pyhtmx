from __future__ import annotations
import sys
from types import TracebackType
from typing import Any, Optional, Union, Dict, List
import re
import xml.etree.ElementTree as etree


PARENT_TAG: Optional[HTMLTag] = None


# Helper functions
def _get_text_content(kwargs: Dict[str, Any]) -> Optional[str]:
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


def _fix_attributes(kwargs: Dict[str, Any]) -> Dict[str, str]:
    new_kwargs = {} 
    for key, value in kwargs.items():
        # Transform lists, dictionaries and other types in a string
        if isinstance(value, list):
            # for a class list
            _value = ' '.join(map(str, value))
        elif isinstance(value, dict):
            # for inline style
            _value = ' '.join(
                map(lambda k, v: f"{k}: {v};", value.keys(), value.values())
            )
        else:
            _value = str(value)
        _key = key.lower()
        # Usual keywords
        if '_' not in _key:
            new_kwargs[_key] = _value
            continue
        # HTMX keywords
        if _key.startswith("hx") or _key.startswith("sse") or _key.startswith("ws"):
            _key = re.sub(r"\_+colon\_+", ':', _key)
            delimiter = '-'
        else:
            # Other keywords (Python reserved words)
            delimiter = "_"
        # Filter out double, leading or trailing underscores
        parts = [*filter(lambda x: x != '',_key.split('_'))]
        new_key = delimiter.join(parts)
        new_kwargs[new_key] = _value

    return new_kwargs


class HTMLTag:
    def __init__(
        self: HTMLTag,
        tag: str,
        inner_content: Optional[Union[str, HTMLTag, List[Union[str, HTMLTag]]]] = None,
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
        self.attributes: Dict[str, str] = _fix_attributes(kwargs)
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
    ) -> None:
        if text_content:
            self._element.text = text_content
        if attributes:
            # TODO: consider updating values incrementally
            # (e.g., adding a class to an existing list)
            formatted_attributes = _fix_attributes(attributes)
            self.attributes.update(formatted_attributes)
            for key, value in formatted_attributes.items():
                self._element.set(key, value)

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
        self._element = etree.Element(self.tag, attrib=self.attributes)
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
        encoded_string = prefix + etree.tostring(self._element, method="html") + suffix
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
