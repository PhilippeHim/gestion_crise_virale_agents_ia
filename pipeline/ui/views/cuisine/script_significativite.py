from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *

def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    dataset = donnees.get("dataset")
    narratif = donnees.get("narratif", {})
    tonalite = narratif.get("tonalite", {}) if isinstance(narratif, dict) else {}
    repartition = tonalite.get("repartition", {}) if isinstance(tonalite, dict) else {}
    certifies = "n/a"
    followers_median = "n/a"
    if isinstance(dataset, pd.DataFrame):
        if "X Verified" in dataset.columns:
            certifies = f"{pd.Series(dataset['X Verified']).fillna(False).astype(bool).sum():,}"
        if "X Followers" in dataset.columns:
            followers = pd.to_numeric(dataset["X Followers"], errors="coerce").dropna()
            if not followers.empty:
                followers_median = f"{int(followers.median()):,}"

    afficher_contrat_agent(
        "Script 1 - significativité sémantique",
        "Sémantique / significativité",
        [
            "Corpus enrichi avec texte normalisé, sentiment, comptes et métadonnées sociales.",
            "Colonnes attendues : Sentiment, X Verified, X Followers, Author.",
            "Sortie NLP de l'agent narratif pour relier thèmes et tonalité.",
        ],
        [
            "Comptage des tonalités positives, neutres et négatives.",
            "Lecture du poids des comptes certifiés et de l'audience médiane.",
            "Croisement entre tonalité, visibilité sociale et récits structurants.",
            "Production d'un signal de significativité avant scoring de risque.",
        ],
        {
            "Négatifs": f"{repartition.get('negative', 0):,}",
            "Neutres": f"{repartition.get('neutral', 0):,}",
            "Certifiés": certifies,
            "Followers méd.": followers_median,
        },
        [
            "Signal sémantique consolidé.",
            "Tonalité exploitable par le filtre de risque.",
            "Indicateurs lisibles pour la proposition client.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_sentiment_global(donnees)
        if fig is not None:
            expliquer_graphe(
                "La matière analysée est-elle plutôt neutre ou hostile ?",
                "Ce script transforme la masse de messages en signal sémantique lisible.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_sentiment_journalier(donnees)
        if fig is not None:
            expliquer_graphe(
                "La tonalité change-t-elle au moment des pics ?",
                "La significativité augmente quand le volume et la négativité montent ensemble.",
            )
            st.plotly_chart(fig, use_container_width=True)
