"""Vue cuisine — Agent 2 : récits détectés, priorisation et déduplication."""

import streamlit as st

from pipeline.ui.charts import (
    graphique_corpus_doublons,
    graphique_recits,
    graphique_recits_risque,
)
from pipeline.ui.view_utils import (
    afficher_badge_fichier_source,
    afficher_contrat_agent,
    expliquer_graphe,
)


def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)

    narratif = donnees.get("narratif") or {}
    if not isinstance(narratif, dict):
        narratif = {}
    recits = narratif.get("recits", [])
    corpus = narratif.get("corpus", {})

    afficher_contrat_agent(
        "Agent 2 - NLP narratif",
        "Narratifs",
        [
            "Corpus texte issu de message_normalizer ou Full Text.",
            "Colonne Sentiment pour évaluer la négativité par récit.",
            "Doublons conservés pour le volume, textes uniques pour l'analyse.",
        ],
        [
            "Nettoyage léger : URLs et espaces.",
            "Déduplication des textes.",
            "Vectorisation TF-IDF, ngrammes 1 à 2, stop words français.",
            "Clustering KMeans pour extraire les récits.",
            "Score de risque = volume relatif + part négative.",
        ],
        {
            "Récits": len(recits),
            "Corpus": corpus.get("messages_total", "n/a"),
            "Analysés": corpus.get("messages_analyses", "n/a"),
        },
        [
            "Liste de récits avec mots-clés, exemple, volume, négativité, score risque.",
            "RAG simple : exemples représentatifs par récit.",
            "Récit prioritaire transmis à Agent 3.",
        ],
    )

    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_recits(donnees)
        if fig is not None:
            expliquer_graphe(
                "Quels récits structurent vraiment la conversation ?",
                "Le volume montre ce qui est visible. La couleur rappelle qu'un récit visible n'est pas toujours le plus agressif.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_recits_risque(donnees)
        if fig is not None:
            expliquer_graphe(
                "Quel récit faut-il traiter en priorité ?",
                "La priorité vient du croisement volume + négativité. Un petit récit très négatif peut être plus sensible qu'un gros récit neutre.",
            )
            st.plotly_chart(fig, use_container_width=True)

    fig = graphique_corpus_doublons(donnees)
    if fig is not None:
        expliquer_graphe(
            "Pourquoi l'agent NLP ignore-t-il une partie des messages ?",
            "Les doublons comptent pour mesurer le volume, mais ils sont retirés pour mieux comprendre les thèmes sans répéter mille fois le même texte.",
        )
        st.plotly_chart(fig, use_container_width=True)
