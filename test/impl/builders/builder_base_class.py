from abc import ABC, abstractmethod


class BuilderBaseClass(ABC):
    @abstractmethod
    def build(self):
        pass
