from typing import Any, Dict, Union
from src.github.models import Label
from .builder_base_class import BuilderBaseClass


class LabelBuilder(BuilderBaseClass):
    def __init__(self, name="label"):
        self.raw_label = {"name": name}

    def name(self, name: str) -> Union["LabelBuilder", Label]:
        self.raw_label["name"] = name
        return self

    def build(self) -> Label:
        return Label(self.raw_label)

    def to_raw(self) -> Dict[str, Any]:
        return self.build().to_raw()
