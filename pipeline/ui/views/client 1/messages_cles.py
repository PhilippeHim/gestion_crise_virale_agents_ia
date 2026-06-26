import streamlit as st


def afficher(donnees: dict) -> None:
    proposition = donnees.get("proposition") or {}
    st.subheader("Messages clés")
    for message in proposition.get("messages_cles", []):
        st.write(f"- {message}")
