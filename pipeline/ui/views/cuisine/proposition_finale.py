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
        "Proposition finale - reformulation, réponse et validation",
        "Proposition / décision",
        [
            "Récit prioritaire issu du filtre de risque.",
            "Tonalité, concentration, amplificateurs et niveau de risque.",
            "Messages clés, points à valider et messages à éviter.",
            "Contraintes : neutralité, prudence, validation humaine.",
        ],
        [
            "Transformation des signaux techniques en diagnostic éditorial.",
            "Choix d'une stratégie de réponse adaptée au risque.",
            "Rédaction d'un brouillon factuel et vérifiable.",
            "Contrôle humain obligatoire avant publication.",
        ],
        {
            "Stratégie": proposition.get("strategie", "n/a"),
            "Risque": proposition.get("niveau_risque", "n/a"),
            "Priorité": proposition.get("priorite", "n/a"),
            "Brouillon": "Disponible" if proposition.get("reponse_brouillon") else "n/a",
            "Messages clés": len(proposition.get("messages_cles", [])),
            "Validation": "Obligatoire",
        },
        [
            "Diagnostic reformulé pour décideur.",
            "Brouillon de réponse non publiable sans validation.",
            "Décision humaine : publier, modifier ou ignorer.",
        ],
    )

    st.markdown("**Synthèse exécutive préparée**")
    st.write(proposition.get("synthese_executive", "Synthèse non disponible."))

    st.markdown("**Brouillon de réponse**")
    st.text_area("Brouillon de réponse", value=proposition.get("reponse_brouillon", ""), height=220)

    col_eviter, col_valider = st.columns(2)
    with col_eviter:
        st.markdown("**À éviter**")
        for item in proposition.get("messages_a_eviter", []):
            st.write(f"- {item}")
    with col_valider:
        st.markdown("**À valider**")
        for item in proposition.get("points_a_valider", []):
            st.write(f"- {item}")
