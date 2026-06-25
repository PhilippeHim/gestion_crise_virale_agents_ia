from pipeline.modules.module import Module


class AgentLangage(Module):
    def run(self) -> dict:
        # Analyse du narratif, du sentiment et des themes.
        return self.etat
