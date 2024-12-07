from __future__ import annotations
from typing import Any, Optional, Union
from html_tag_list import HTML_TAGS
from html_tag import HTMLTag


def tag_class_factory(tag: str):
    def __init__(
        self: HTMLTag,
        content: Optional[Union[str, HTMLTag, list[Union[str, HTMLTag]]]] = None,
        **kwargs: Any,
    ):
        HTMLTag.__init__(self, tag, content=content, **kwargs)
    tag_class = type(tag.title(), (HTMLTag, ), {"__init__": __init__})
    return tag_class

for tag in HTML_TAGS:
    globals()[tag.title()] = tag_class_factory(tag)