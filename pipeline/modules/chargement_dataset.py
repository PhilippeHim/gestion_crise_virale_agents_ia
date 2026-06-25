from pipeline.modules.module import Module


class ChargementDataset(Module):
    def run(self) -> dict:
        # Charge le fichier XLSX et stocke le resultat dans etat["dataset"].
        return self.etat
