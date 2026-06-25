from pipeline.modules.module import Module


class Declencheur(Module):
    def run(self) -> dict:
        # Si le declencheur vaut 0, la pipeline s'arrete.
        if self.etat.get("declencheur") == 0:
            self.etat["arreter_pipeline"] = True
        return self.etat
