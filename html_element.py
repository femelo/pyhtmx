from __future__ import annotations
import sys
from types import TracebackType
from typing import Any, Optional, Union, TextIO
import xml.etree.ElementTree as etree

PARENT_TAG: Optional[HTMLElement] = None


def snake_to_camel_case(input_string: str) -> str:
    parts = list(
        filter(
            lambda part: part != '',
            input_string.split("_")
        )
    )
    output_string = ''.join(
        [
            parts[0].lower(),
            *map(str.title, parts[1:]),
        ]
    )
    return output_string



class HTMLElement:
    def __init__(
        self: HTMLElement,
        tag: str,
        children: Optional[Union[list[HTMLElement], HTMLElement]] = None,
        **kwargs: Any,
    ):
        self.tag = tag 
        # Get children
        if children is None:
            self.children = []
        elif isinstance(children, HTMLElement):
            self.children = [children]
        else:
            self.children = children
        # Get element content
        text: Optional[str] = None
        for field in ("text", "text_content", "content", "inner_html"):
            if field in kwargs:
                text = kwargs.pop(field)
                continue
            field_camel_case = snake_to_camel_case(field)
            if field_camel_case in kwargs:
                text = kwargs.pop(field_camel_case)
        # Other attributes
        self.attributes: dict[str, Any] = kwargs
        self._parent: Optional[HTMLElement] = None
        self._level: int = 0
        self._element: Optional[etree.Element] = None
        # Build element
        self._build_element(text=text)
        self._set_parent()

    @property
    def parent(self: HTMLElement) -> Optional[HTMLElement]:
        return self._parent

    @parent.setter
    def parent(self: HTMLElement, value: Optional[HTMLElement]) -> None:
        self._parent = value
        if self._parent is not None and self._parent._element is not None:
            self._parent._element.append(self._element)

    @property
    def level(self: HTMLElement) -> int:
        return self._level

    @level.setter
    def level(self: HTMLElement, value: int) -> None:
        self._level = value

    @property
    def tree(self: HTMLElement) -> etree.ElementTree:
        return etree.ElementTree(self._element)

    @property
    def text(self: HTMLElement) -> Optional[str]:
        return self._element.text

    @text.setter
    def text(self: HTMLElement, value: Optional[str]) -> None:
        self._element.text = value

    def _build_element(self: HTMLElement, text: Optional[str] = None) -> None:
        self._element = etree.Element(self.tag, attrib=self.attributes)
        if text is not None:
            self._element.text = text

    def _set_parent(self: HTMLElement) -> None:
        for child in self.children:
            child.parent = self
            child.level = self.level + 1

    def __enter__(self: HTMLElement) -> HTMLElement:
        global PARENT_TAG
        if PARENT_TAG is not None:
            self.parent = PARENT_TAG
            self.level = self.parent.level + 1
        PARENT_TAG = self
        return self

    def __exit__(
        self: HTMLElement,
        typ: Optional[type] = None,
        value: Optional[Exception] = None,
        traceback: Optional[TracebackType] = None,
    ) -> None:
        global PARENT_TAG
        if PARENT_TAG is self:
            PARENT_TAG = self._parent

    def to_string(
        self: HTMLElement,
        space: str = 4 * " ",
        level: Optional[int] = None,
    ) -> str:
        if level is None:
            level = self.level
        etree.indent(self._element, space=space, level=level)
        prefix = (level * space).encode()
        suffix = b'' if level > 0 else b'\n'
        encoded_string = prefix + etree.tostring(self._element, method="html") + suffix
        return encoded_string.decode()

    def write(
        self: HTMLElement,
        filename: str,
        space: str = 4 * " ",
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
        self: HTMLElement, space:
        str = 4 * " ",
        level: Optional[int] = None,
    ) -> None:
        if level is None:
            level = self.level
        etree.indent(self._element, space=space, level=level)
        if level > 0:
            sys.stdout.write(level * space)
        etree.dump(self._element)
