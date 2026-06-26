from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *

def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    dataset = donnees.get("dataset")
    classes = dataset["Classe_viralite"].value_counts().to_dict() if isinstance(dataset, pd.DataFrame) and "Classe_viralite" in dataset else {}
    afficher_contrat_agent(
        "Agent 1 - ce message peut-il être viral ?",
        "Propagation / priorisation",
        [
            "DataFrame enrichi par les acteurs et la propagation.",
            "Colonnes attendues : X Followers, X Verified, X Posts, Hashtags, Full Text.",
            "Chaque ligne est transformée en features numériques.",
        ],
        [
            "Modèle utilisé : sklearn Pipeline sauvegardé en joblib.",
            "Features : followers, compte vérifié, volume de posts, nombre de hashtags, longueur du texte.",
            "Sortie probabiliste si predict_proba existe.",
            "Classification par seuils : Non Viral, Moyennement Viral, Viral.",
        ],
        {
            "Viral": classes.get("Viral", 0),
            "Moyen": classes.get("Moyennement Viral", 0),
            "Non viral": classes.get("Non Viral", 0),
        },
        [
            "Colonnes ajoutées : Viralite et Classe_viralite.",
            "Décision de continuer si au moins un contenu est viral.",
            "Signal de priorité pour la suite narrative.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_viralite_distribution(donnees)
        if fig is not None:
            expliquer_graphe(
                "Combien de contenus méritent une attention prioritaire ?",
                "L'agent ne dit pas que tout est grave : il trie les messages selon leur potentiel d'exposition.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_viralite_reach(donnees)
        if fig is not None:
            expliquer_graphe(
                "La viralité vient-elle de gros comptes ou de contenus très relayés ?",
                "Un point haut avec peu d'abonnés signale une amplification collective ; un point haut avec beaucoup d'abonnés signale une audience structurelle.",
            )
            st.plotly_chart(fig, use_container_width=True)
