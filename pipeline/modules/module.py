from abc import ABC, abstractmethod
from typing import Any


class Module(ABC):
    def __init__(self, etat: dict) -> None:
        self.etat = etat
        self.donnees: Any = None
        self.graphique: Any = None

    @abstractmethod
    def run(self) -> dict:
        pass
