from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *


def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    dataset = donnees.get("dataset")
    pic = donnees.get("proposition", {}).get("chiffres_cles", {}).get("pic", {})
    alerte = etat_alerte_trigger_volume(donnees)
    seuil = alerte["seuil"]
    messages_au_dessus = alerte["messages_au_dessus"]
    concentration = donnees.get("concentration", {})

    auteurs_uniques = "n/a"
    comptes_certifies = "n/a"
    if isinstance(dataset, pd.DataFrame):
        if "Author" in dataset.columns:
            auteurs_uniques = f"{dataset['Author'].nunique():,}"
        if "X Verified" in dataset.columns:
            comptes_certifies = f"{pd.Series(dataset['X Verified']).fillna(False).astype(bool).sum():,}"

    afficher_contrat_agent(
        "Déclencheurs - volume, alerte et significativité",
        "Déclencheur / propagation",
        [
            "Messages datés avec Date, Impressions, Author, X Verified et Engagement Type.",
            "Seuil d'alerte attendu : SEUIL_IMPRESSION, défaut 5000.",
            "Dataset filtré et nettoyé par la collecte et les filtres.",
        ],
        [
            "Conversion des impressions en valeurs numériques.",
            "Recherche des messages au-dessus du seuil d'alerte.",
            "Agrégation quotidienne pour repérer le pic de volume.",
            "Calcul de concentration : Gini contenu, Gini relais, part du top 20.",
            "Lecture des comptes uniques, certifiés et sources amplifiées.",
        ],
        {
            "Messages": f"{len(dataset):,}" if isinstance(dataset, pd.DataFrame) else "n/a",
            "Seuil": f"{seuil:,}",
            "Au-dessus": f"{messages_au_dessus:,}",
            "Pic": f"{pic.get('messages', 0):,}",
            "Auteurs uniques": auteurs_uniques,
            "Certifiés": comptes_certifies,
            "Gini contenu": concentration.get("gini_contenu", "n/a"),
            "Top 20 RT": f"{concentration.get('top20_share_pct', 'n/a')}%",
        },
        [
            "Signal déclencheur pour l'écran Propagation.",
            "Niveau de significativité transmis aux agents suivants.",
            "Pic temporel, sources amplifiées et concentration du relais.",
        ],
    )

    if alerte["alerte"]:
        st.markdown('<div style="text-align:center"><span class="px8-red-alert">Red Alert</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center"><span class="px8-no-alert">Aucune alerte</span></div>', unsafe_allow_html=True)

    col_volume, col_gini = st.columns(2)
    with col_volume:
        fig = graphique_volume_journalier(donnees)
        if fig is not None:
            expliquer_graphe(
                "Quand le sujet franchit-il un seuil visible ?",
                "Le trigger volume repère le moment où la crise cesse d'être diffuse et devient observable dans le flux.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_gini:
        graphique_gini = donnees.get("graphique_gini")
        if graphique_gini is not None:
            expliquer_graphe(
                "Le relais est-il concentré entre quelques sources ?",
                "Un Gini élevé indique qu'une petite partie des contenus ou relais structure fortement la circulation.",
            )
            st.plotly_chart(graphique_gini, use_container_width=True)

    graphique_amplificateurs = donnees.get("graphique_amplificateurs")
    if graphique_amplificateurs is not None:
        expliquer_graphe(
            "Qui porte la propagation visible ?",
            "Les premiers amplificateurs montrent les sources qui donnent de la portée au sujet.",
        )
        st.plotly_chart(graphique_amplificateurs, use_container_width=True)
