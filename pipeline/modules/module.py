from abc import ABC, abstractmethod
from typing import Any


class Module(ABC):
    def __init__(self, donnees: dict) -> None:
        self.donnees = donnees

    @abstractmethod
    def run(self) -> dict:
        pass
