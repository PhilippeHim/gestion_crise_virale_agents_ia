from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *

def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    communaute = donnees.get("communaute", {})
    communautes = donnees.get("communautes", [])
    afficher_contrat_agent(
        "Brique coordination - qui amplifie ensemble ?",
        "Coordination / polarisation",
        [
            "Retweets avec Author et _source.",
            "Sources relayées au moins 10 fois.",
            "Graphe biparti retweeteur <-> source amplifiée.",
        ],
        [
            "Construction d'un graphe NetworkX pondéré.",
            "Détection de communautés par algorithme de Louvain.",
            "Calcul de modularité.",
            "Filtrage des communautés sous le seuil de messages.",
        ],
        {
            "Communautés": len(communautes),
            "Modularité": communaute.get("modularite", "n/a") if isinstance(communaute, dict) else "n/a",
            "Auteurs": communaute.get("nombre_auteurs_communautarises", "n/a") if isinstance(communaute, dict) else "n/a",
        },
        [
            "Liste de communautés caractérisées.",
            "Sources pivots par communauté.",
            "Dataset communautaire envoyé à l'analyse de langage.",
        ],
    )
    if communautes:
        col_gauche, col_droite = st.columns(2)
        with col_gauche:
            fig = graphique_communautes_risque(donnees)
            if fig is not None:
                expliquer_graphe(
                    "Quelles communautés sont grosses, négatives et structurées ?",
                    "La taille représente le nombre de retweeteurs. Une communauté haut placée est plus négative ; à droite, elle pèse plus en volume.",
                )
                st.plotly_chart(fig, use_container_width=True)
        with col_droite:
            fig = graphique_sources_pivots(donnees)
            if fig is not None:
                expliquer_graphe(
                    "Quels comptes ou sources servent de points de ralliement ?",
                    "Ces sources pivots ne sont pas forcément les plus bavardes : ce sont celles que les communautés amplifient ensemble.",
                )
                st.plotly_chart(fig, use_container_width=True)

        table_communautes = dataframe_communautes(donnees)
        table_communautes = table_communautes.drop(columns=["sources_lisibles"], errors="ignore")
        st.markdown("**Table de contrôle : communautés détectées par Louvain**")
        st.dataframe(dataframe_tableau_lisible(table_communautes), use_container_width=True, hide_index=True)
