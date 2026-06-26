import streamlit as st


def afficher(donnees: dict) -> None:
    proposition = donnees.get("proposition") or {}
    st.subheader("Brouillon de réponse")
    st.text_area(
        "Texte de travail",
        value=proposition.get("reponse_brouillon", ""),
        height=180,
    )
