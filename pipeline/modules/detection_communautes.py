from pipeline.modules.module import Module


class DetectionCommunautes(Module):
    def run(self) -> dict:
        # Identifie les communautes et agrege leurs metriques.
        return self.etat
