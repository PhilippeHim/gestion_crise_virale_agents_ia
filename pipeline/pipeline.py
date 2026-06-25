from collections.abc import Sequence
from typing import Any
from pipeline.modules import module
from pipeline.modules.agent_langage import AgentLangage
from pipeline.modules.agent_proposition import AgentProposition
from pipeline.modules.agent_viralite import AgentViralite
from pipeline.modules.chargement_dataset import ChargementDataset
from pipeline.modules.declencheur import Declencheur
from pipeline.modules.detection_communautes import DetectionCommunautes
from pipeline.modules.module import Module


class PipelineAgentX(Module):

    def __init__(self) -> None:

        self.modules = [
            ChargementDataset,
            Declencheur,
            AgentViralite,
            DetectionCommunautes,
            AgentLangage,
            AgentProposition,
        ]

        self.donnees = {
            "dataset": None,
            "declencheur": False,
            "communautes": list(),
            "proposition": None,
            "arreter_pipeline": False,
            "path": None
        }

    def run(self, path) -> dict:
        self.donnees["arreter_pipeline"] = False
        self.donnees["path"] = path

        for module_class in self.modules:
            module = module_class(self.donnees)
            self.donnees = module.run()
            if self.donnees["arreter_pipeline"]: break
            
        return self.donnees



