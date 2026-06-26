from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *

def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    concentration = donnees.get("concentration", {})
    pic = donnees.get("proposition", {}).get("chiffres_cles", {}).get("pic", {})
    afficher_contrat_agent(
        "Brique propagation - quand la crise bascule ?",
        "Propagation",
        [
            "Messages datés avec Date, Impressions, Engagement Type.",
            "Seuil d'impressions configurable : SEUIL_IMPRESSION, défaut 5000.",
            "Retweets enrichis avec source amplifiée.",
        ],
        [
            "Détection d'au moins un message au-dessus du seuil d'impressions.",
            "Calcul de concentration des sources amplifiées.",
            "Indice de Gini contenu et relais.",
            "Part des 20 premières sources dans les retweets.",
        ],
        {
            "Pic": f"{pic.get('messages', 0):,}",
            "Date pic": pic.get("date", "n/a"),
            "Gini contenu": concentration.get("gini_contenu", "n/a"),
            "Top 20 RT": f"{concentration.get('top20_share_pct', 'n/a')}%",
        },
        [
            "Signal de poursuite ou arrêt de la pipeline.",
            "Amplificateurs principaux.",
            "Graphiques Gini et amplificateurs.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_volume_journalier(donnees)
        if fig is not None:
            expliquer_graphe(
                "À quel moment la conversation devient-elle une crise visible ?",
                "Les pics indiquent les jours où le sujet sort du bruit normal. C'est le moment à relier aux événements et aux relais majeurs.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_sentiment_journalier(donnees)
        if fig is not None:
            expliquer_graphe(
                "Le pic est-il seulement volumétrique ou aussi émotionnel ?",
                "Si la zone négative monte avec le volume, la crise n'est pas seulement bruyante : elle devient réputationnelle.",
            )
            st.plotly_chart(fig, use_container_width=True)
    amplificateurs = donnees.get("amplificateurs")
    if isinstance(amplificateurs, pd.DataFrame):
        st.markdown("**Sources amplifiées : qui sert de point d'appui au relais ?**")
        st.dataframe(amplificateurs.head(10), use_container_width=True, hide_index=True)
