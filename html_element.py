from __future__ import annotations
from types import TracebackType
from typing import Any, Optional, Union
import xml.etree.ElementTree as etree

PARENT_TAG: Optional[HTMLElement] = None

class HTMLElement:
    def __init__(
        self: HTMLElement,
        tag: str,
        children: Optional[Union[list[HTMLElement], HTMLElement]] = None,
        **kwargs: Any,
    ):
        self.tag = tag 
        if children is None:
            self.children = []
        elif isinstance(children, HTMLElement):
            self.children = [children]
        else:
            self.children = children
        self.attributes: dict[str, Any] = kwargs
        self._parent: Optional[HTMLElement] = None
        self._element: Optional[etree.Element] = None
        self._text: Optional[str] = None
        self._build_element()
        self._set_parent()

    @property
    def parent(self: HTMLElement) -> Optional[HTMLElement]:
        return self._parent
    
    @parent.setter
    def parent(self: HTMLElement, value: Optional[HTMLElement]) -> None:
        self._parent = value
        if self._parent._element is not None:
            self._parent._element.append(self._element)

    @property
    def text(self: HTMLElement) -> Optional[str]:
        return self._text

    @text.setter
    def text(self: HTMLElement, value: Optional[str]) -> None:
        self._text = value
        self.element.text = value

    def write(self: HTMLElement, filename: str) -> None:
        etree.ElementTree(self.element).write(filename)

    def _build_element(self: HTMLElement) -> None:
        self._element = etree.Element(self.tag, attrib=self.attributes)

    def _set_parent(self: HTMLElement) -> None:
        for child in self.children:
            child.parent = self._element

    def __enter__(self: HTMLElement) -> HTMLElement:
        global PARENT_TAG
        if PARENT_TAG is not None:
            self._parent = PARENT_TAG
            self._append_to_parent()
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
