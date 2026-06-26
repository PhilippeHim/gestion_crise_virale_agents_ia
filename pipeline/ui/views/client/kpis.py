import streamlit as st

from pipeline.ui.view_utils import (
    derniere_collecte_lisible,
    mots_recits_lisibles,
    signaux_priorite_lisibles,
)


def afficher(donnees: dict) -> None:
    proposition = donnees.get("proposition") or {}
    chiffres = proposition.get("chiffres_cles", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Messages analysés", f"{chiffres.get('messages_analyses', 0):,}", derniere_collecte_lisible(donnees))
    pic = chiffres.get("pic", {})
    col2.metric("Pic maximal", f"{pic.get('messages', 0):,}", pic.get("date", "n/a"))
    col3.metric("Récits structurants", chiffres.get("nombre_recits", 0), mots_recits_lisibles(donnees))
    col4.metric("Priorité", proposition.get("priorite", "n/a"), signaux_priorite_lisibles(donnees))
