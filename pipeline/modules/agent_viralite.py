from pipeline.modules.module import Module


class AgentViralite(Module):
    def run(self) -> dict:
        # Analyse les signaux de viralite du message.
        return self.etat
