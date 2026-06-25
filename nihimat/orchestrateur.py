"""
crisis_agents.orchestrateur — Enchaînement séquentiel des 3 agents
------------------------------------------------------------------
Pipeline : Veille (pic + amplificateurs) -> Narratif (récits + risque) -> Rédacteur (réponses
ancrées) -> VALIDATION HUMAINE. La priorisation est explicite : on ne rédige par défaut que
pour les récits au risque le plus élevé (le reste reste en veille). Générique (SchemaConfig).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import pandas as pd

from .config import SchemaConfig
from .veille import AgentVeille, VeilleResult
from .narratif import AgentNarratif, NarratifResult
from .redacteur import AgentRedacteur, DraftResponse
from .llm import LLMClient


@dataclass
class CrisisReport:
    veille: VeilleResult
    narratif: NarratifResult
    responses: list           # DraftResponse (brouillons à valider)
    brief: str
    def __repr__(self): return self.brief


class Orchestrateur:
    def __init__(self, cfg: SchemaConfig = SchemaConfig(), llm: Optional[LLMClient] = None,
                 method: str = "tfidf", k: int = 6, draft_top_n: int = 3):
        self.cfg, self.llm, self.method, self.k = cfg, llm, method, k
        self.draft_top_n = draft_top_n   # nb de récits (par risque) pour lesquels on rédige

    def run(self, df: pd.DataFrame, institutional_account: Optional[str] = None,
            organization: Optional[str] = None, targets: Optional[list] = None) -> CrisisReport:
        # 1) Veille
        veille = AgentVeille(self.cfg).run(df, institutional_account=institutional_account)
        # 2) Narratif
        narratif = AgentNarratif(self.cfg, llm=self.llm, method=self.method, k=self.k).run(df)
        # 3) Rédacteur — priorisation par risque (sauf cibles imposées)
        if targets is None:
            targets = [int(n.nid) for n in narratif.narratives[:self.draft_top_n]]  # déjà triés par risque
        responses = AgentRedacteur(self.cfg, llm=self.llm, organization=organization)\
                        .run(df, narratif.narratives, targets=targets)

        return CrisisReport(veille, narratif, responses, self._brief(veille, narratif, responses, targets))

    def _brief(self, veille, narratif, responses, targets):
        L = ["#" * 60, "# RAPPORT DE CRISE — pipeline Veille → Narratif → Rédacteur", "#" * 60, ""]
        L.append(veille.brief); L.append("")
        L.append(narratif.brief); L.append("")
        L.append(f"=== AGENT RÉDACTEUR — {len(responses)} brouillon(s) (récits prioritaires {targets}) ===")
        for r in responses:
            preview = r.draft.replace("\n", " ")[:90]
            L.append(f"  • {r.narrative_name} : {preview}…")
        L.append("")
        L.append(">>> ÉTAPE SUIVANTE : VALIDATION HUMAINE obligatoire avant toute diffusion. <<<")
        return "\n".join(L)
