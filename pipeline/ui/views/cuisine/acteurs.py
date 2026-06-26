from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *

def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame):
        st.info("Dataset non chargé.")
        return

    top_auteurs = dataset["Author"].value_counts().head(10).reset_index()
    top_auteurs.columns = ["Auteur", "Messages"]
    originaux = int(dataset.get("_is_original", pd.Series(dtype=bool)).sum()) if "_is_original" in dataset else 0
    retweets = int((dataset.get("Engagement Type") == "RETWEET").sum()) if "Engagement Type" in dataset else 0

    afficher_contrat_agent(
        "Brique acteurs - qui parle et qui relaie ?",
        "Acteurs",
        [
            "Dataset préparé par ChargementDataset.",
            "Colonnes attendues : Author, X Followers, X Verified, Engagement Type, X Repost of.",
            f"Volume reçu : {len(dataset):,} lignes et {len(dataset.columns):,} colonnes.",
        ],
        [
            "Extraction des auteurs originaux depuis les URL de repost.",
            "Séparation messages originaux / retweets / réponses.",
            "Comptage des auteurs actifs et des sources amplifiées.",
            "Préparation du terrain pour les agents viralité et coordination.",
        ],
        {
            "Messages": f"{len(dataset):,}",
            "Auteurs": f"{dataset['Author'].nunique():,}" if "Author" in dataset else "n/a",
            "Originaux": f"{originaux:,}",
            "Retweets": f"{retweets:,}",
        },
        [
            "DataFrame enrichi avec _source, _status_id, _is_original.",
            "Liste des auteurs et sources mobilisables par viralité / coordination.",
        ],
    )
    col_gauche, col_droite = st.columns([1.1, 0.9])
    with col_gauche:
        fig = graphique_top_auteurs(donnees)
        if fig is not None:
            expliquer_graphe(
                "Quels comptes produisent ou relaient le plus de messages ?",
                "Plus la barre est longue, plus le compte pèse dans le bruit total. Cela identifie les acteurs à surveiller avant de parler de narratif.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_types_engagement(donnees)
        if fig is not None:
            expliquer_graphe(
                "Est-ce une crise de prise de parole ou surtout d'amplification ?",
                "Une forte part de retweets signifie que la dynamique vient surtout du relais collectif, pas seulement de nouveaux messages originaux.",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Table de contrôle : top auteurs**")
    st.dataframe(top_auteurs, use_container_width=True, hide_index=True)
