from pipeline.modules.module import Module


class AgentProposition(Module):
    def run(self) -> dict:
        # Propose une action: ignorer, publier ou modifier.
        return self.etat
