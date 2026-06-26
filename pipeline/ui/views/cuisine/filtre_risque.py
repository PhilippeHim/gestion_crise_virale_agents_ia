from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *

def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
    recit_prioritaire = max(recits, key=lambda recit: recit.get("score_risque", 0), default={})

    afficher_contrat_agent(
        "Filtre 3 - risque sémantique",
        "Sémantique / risque",
        [
            "Récits issus de l'agent NLP.",
            "Pour chaque récit : volume, part négative, score de risque et exemples.",
            "Signal de significativité produit par Script 1.",
        ],
        [
            "Croisement volume relatif + agressivité / négativité.",
            "Priorisation des récits qui combinent visibilité et danger réputationnel.",
            "Filtrage des signaux faibles trop peu structurés.",
            "Sélection du récit à traiter dans la proposition finale.",
        ],
        {
            "Récits": len(recits),
            "Prioritaire": recit_prioritaire.get("nom", "n/a"),
            "Score": recit_prioritaire.get("score_risque", "n/a"),
            "% nég.": f"{recit_prioritaire.get('pct_negative', 'n/a')}%",
        },
        [
            "Récit prioritaire qualifié.",
            "Niveau de risque transmis à Sémantique et Proposition.",
            "Arguments pour décider quoi répondre, et quoi éviter.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_recits_risque(donnees)
        if fig is not None:
            expliquer_graphe(
                "Quel récit est le plus risqué, pas seulement le plus visible ?",
                "Le filtre évite de répondre au bruit majoritaire si un récit plus petit est beaucoup plus agressif.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_recits(donnees)
        if fig is not None:
            expliquer_graphe(
                "Comment le risque se répartit-il entre les récits ?",
                "Cette lecture prépare la décision éditoriale : prioriser, temporiser ou ignorer.",
            )
            st.plotly_chart(fig, use_container_width=True)
