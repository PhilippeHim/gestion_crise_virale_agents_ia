from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *

def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    tonalite = donnees.get("narratif", {}).get("tonalite", {})
    repartition = tonalite.get("repartition", {}) if isinstance(tonalite, dict) else {}
    afficher_contrat_agent(
        "Brique sémantique - quelle tonalité domine ?",
        "Sémantique / sentiment",
        [
            "Colonne Sentiment déjà présente dans le corpus.",
            "Messages groupés par récit et communauté.",
            "Texte normalisé pour relier tonalité et narratif.",
        ],
        [
            "Répartition positive / neutre / négative.",
            "Calcul de part négative globale.",
            "Calcul de part négative par récit et par communauté.",
            "Utilisation de la négativité comme facteur de risque.",
        ],
        {
            "Négatif": f"{tonalite.get('part_negative', 'n/a')}%",
            "Neutre": f"{tonalite.get('part_neutral', 'n/a')}%",
            "Positif": f"{tonalite.get('part_positive', 'n/a')}%",
        },
        [
            "Tonalité globale de crise.",
            "Récits plus dangereux que leur seul volume.",
            "Arguments de priorisation pour la proposition finale.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_sentiment_global(donnees)
        if fig is not None:
            expliquer_graphe(
                "La conversation est-elle majoritairement hostile ?",
                "Le sentiment global donne la température de la crise : neutre, défensive, ou franchement négative.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_sentiment_journalier(donnees)
        if fig is not None:
            expliquer_graphe(
                "La négativité se concentre-t-elle sur certains jours ?",
                "Une montée courte et intense appelle une réponse rapide ; une négativité durable appelle plutôt une stratégie de clarification dans le temps.",
            )
            st.plotly_chart(fig, use_container_width=True)
