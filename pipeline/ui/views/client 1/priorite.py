import streamlit as st


def afficher(donnees: dict) -> None:
    proposition = donnees.get("proposition") or {}
    recit_prioritaire = proposition.get("recit_prioritaire", {})

    st.subheader("Priorité de communication")
    gauche, droite = st.columns([1.2, 1])
    with gauche:
        st.markdown(f"**Stratégie recommandée :** {proposition.get('strategie', 'n/a')}")
        st.markdown(f"**Délai recommandé :** {proposition.get('delai_recommande', 'n/a')}")
        st.markdown(f"**Niveau de risque :** {proposition.get('niveau_risque', 'n/a')}")
        if recit_prioritaire:
            st.markdown(f"**Récit à traiter en priorité :** {recit_prioritaire.get('nom', 'n/a')}")
            st.caption(
                f"Volume {recit_prioritaire.get('volume', 'n/a')} · "
                f"{recit_prioritaire.get('pct_negative', 'n/a')}% négatif · "
                f"score risque {recit_prioritaire.get('score_risque', 'n/a')}"
            )
    with droite:
        st.info(proposition.get("notice_validation", "Validation humaine obligatoire."))
