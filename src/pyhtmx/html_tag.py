from __future__ import annotations
import sys
from types import TracebackType
from typing import Any, Optional, Union
import re
import xml.etree.ElementTree as etree


PARENT_TAG: Optional[HTMLTag] = None


# Helper functions
def _get_text_content(**kwargs: Any) -> Optional[str]:
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


def _fix_attributes(**kwargs: Any) -> dict[str, str]:
    new_kwargs = {} 
    for key, value in kwargs.items():
        _key = key.lower()
        # Usual keywords
        if '_' not in key:
            new_kwargs[_key] = value
            continue
        # HTMX keywords
        if _key.startswith("hx") or _key.startswith("sse") or _key.startswith("ws"):
            _key = re.sub(r"\_+colon\_+", ':', _key)
            delimiter = '-'
        else:
        # Other keywords (Python reserved words)
            _key = key.lower()
            delimiter = "_"
        # Filter out double, leading or trailing underscores
        parts = [*filter(lambda x: x != '',_key.split('_'))]
        new_key = delimiter.join(parts)
        new_kwargs[new_key] = value

    return new_kwargs


class HTMLTag:
    def __init__(
        self: HTMLTag,
        tag: str,
        content: Optional[Union[str, HTMLTag, list[Union[str, HTMLTag]]]] = None,
        **kwargs: Any,
    ):
        self.tag = tag
        # Get text content and children, when available
        text_content: Optional[str] = None
        if content is None:
            self.children = []
        elif isinstance(content, str):
            text_content = content
            self.children = []
        elif isinstance(content, HTMLTag):
            self.children = [content]
        else:
            self.children = list(
                map(
                    lambda child: HTMLTag("span", child)
                    if isinstance(child, str) else child,
                    content,
                ),
            )
        # Check whether text content was specified with keyword argument
        kw_text_content = _get_text_content(**kwargs)
        text_content = text_content or kw_text_content
        # Other attributes
        self.attributes: dict[str, Any] = _fix_attributes(**kwargs)
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
        self._parent = value
        if self._parent is not None and self._parent._element is not None:
            self._parent._element.append(self._element)

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
        for child in self.children:
            child.parent = self
            child.level = self.level + 1

    def __enter__(self: HTMLTag) -> HTMLTag:
        global PARENT_TAG
        if PARENT_TAG is not None:
            self.parent = PARENT_TAG
            self.level = self.parent.level + 1
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
            PARENT_TAG = self._parent

    def to_string(
        self: HTMLTag,
        space: str = 2 * " ",
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
