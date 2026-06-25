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
            "historique_modules": [],
            "path": None,
        }

    def run(self, path) -> dict:
        self.donnees["arreter_pipeline"] = False
        self.donnees["historique_modules"] = []
        self.donnees["path"] = path

        for classe_module in self.modules:
            nom_module = classe_module.__name__
            trace = {
                "module": nom_module,
                "statut": "en cours",
                "lignes_avant": self._nombre_lignes_dataset(),
            }

            try:
                module = classe_module(self.donnees)
                self.donnees = module.run()
                trace["statut"] = "fait"
                trace["lignes_apres"] = self._nombre_lignes_dataset()
                trace["arreter_pipeline"] = self.donnees["arreter_pipeline"]
                print(f"Module {nom_module} execute.")
            except Exception as erreur:
                trace["statut"] = "erreur"
                trace["erreur"] = f"{type(erreur).__name__}: {erreur}"
                self.donnees["erreur_pipeline"] = trace["erreur"]
                self.donnees["arreter_pipeline"] = True

            self.donnees["historique_modules"].append(trace)

            if self.donnees["arreter_pipeline"]:
                break

        return self.donnees

    def _nombre_lignes_dataset(self):
        dataset = self.donnees.get("dataset")
        return len(dataset) if dataset is not None else None
