import streamlit as st


def afficher(donnees: dict) -> None:
    proposition = donnees.get("proposition") or {}
    st.subheader("Diagnostic")
    st.write(proposition.get("synthese_executive", "Synthèse non disponible."))

    diagnostic = proposition.get("diagnostic", [])
    if diagnostic:
        for point in diagnostic:
            st.write(f"- {point}")
