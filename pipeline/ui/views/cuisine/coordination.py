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
            "Modularité": communaute.get("modularite", "n/a")
            if isinstance(communaute, dict)
            else "n/a",
            "Auteurs": communaute.get("nombre_auteurs_communautarises", "n/a")
            if isinstance(communaute, dict)
            else "n/a",
        },
        [
            "Liste de communautés caractérisées.",
            "Sources pivots par communauté.",
            "Dataset communautaire envoyé à l'analyse de langage.",
        ],
    )
    if not communautes:
        st.info("Aucune communauté détectée pour le moment.")
        return

    ids_disponibles = [str(c.get("id")) for c in communautes if c.get("id") is not None]
    ids_disponibles = sorted(
        dict.fromkeys(ids_disponibles), key=lambda x: int(x) if x.isdigit() else x
    )

    ids_selectionnes = st.multiselect(
        "Filtrer les communautés",
        options=ids_disponibles,
        default=ids_disponibles,
    )

    communautes_filtrees = [
        c for c in communautes if str(c.get("id")) in set(ids_selectionnes)
    ]
    donnees_filtrees = {**donnees, "communautes": communautes_filtrees}

    onglet_graph_commu, onglet_graph_sources, onglet_table = st.tabs(
        [
            "Graphique communautés",
            "Graphique sources pivots",
            "Table communautés",
        ]
    )

    with onglet_graph_commu:
        fig = graphique_communautes_risque(donnees_filtrees)
        if fig is None:
            st.info("Aucune donnée à afficher avec ce filtre.")
        else:
            st.plotly_chart(fig, use_container_width=True)

    with onglet_graph_sources:
        fig = graphique_sources_pivots(donnees_filtrees)
        if fig is None:
            st.info("Aucune donnée à afficher avec ce filtre.")
        else:
            st.plotly_chart(fig, use_container_width=True)

    with onglet_table:
        table_communautes = dataframe_communautes(donnees_filtrees)
        table_communautes = table_communautes.drop(
            columns=["sources_lisibles"], errors="ignore"
        )
        if table_communautes.empty:
            st.info("Aucune ligne à afficher avec ce filtre.")
        else:
            st.dataframe(
                dataframe_tableau_lisible(table_communautes),
                use_container_width=True,
                hide_index=True,
            )
