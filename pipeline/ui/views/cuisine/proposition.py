from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *

def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    proposition = donnees.get("proposition", {})
    afficher_contrat_agent(
        "Agent 3 - proposition de réponse",
        "Réponse / orchestration",
        [
            "Récit prioritaire, tonalité, concentration, amplificateurs.",
            "Sorties validées des agents précédents.",
            "Contraintes : neutralité, pas d'invention, validation humaine.",
        ],
        [
            "Synthèse exécutive de la crise.",
            "Choix d'une stratégie : clarification factuelle.",
            "Identification des messages clés, risques, éléments à éviter.",
            "Rédaction d'un brouillon avec placeholders obligatoires.",
        ],
        {
            "Priorité": proposition.get("priorite", "n/a"),
            "Risque": proposition.get("niveau_risque", "n/a"),
            "Stratégie": proposition.get("strategie", "n/a"),
        },
        [
            "Vue client final.",
            "Brouillon non publiable sans validation.",
            "Décision humaine : publier, modifier ou ignorer.",
        ],
    )
    st.text_area("Brouillon Agent 3", value=proposition.get("reponse_brouillon", ""), height=180)
