import streamlit as st


def afficher(donnees: dict) -> None:
    proposition = donnees.get("proposition") or {}
    col_eviter, col_valider = st.columns(2)
    with col_eviter:
        st.subheader("À éviter")
        for item in proposition.get("messages_a_eviter", []):
            st.write(f"- {item}")
    with col_valider:
        st.subheader("À valider")
        for item in proposition.get("points_a_valider", []):
            st.write(f"- {item}")
