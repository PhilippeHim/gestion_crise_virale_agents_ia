import streamlit as st

from pipeline.ui.router import afficher_vue_cuisine, afficher_vue_vide
from pipeline.ui.view_utils import appliquer_style_typographique, afficher_header_principal_avec_toggle


def main() -> None:
    st.set_page_config(page_title="Pipeline Agent X", layout="wide")
    appliquer_style_typographique()

    if "donnees_pipeline" not in st.session_state:
        afficher_vue_vide()
        st.stop()

    mode_vue = afficher_header_principal_avec_toggle()
    donnees = st.session_state["donnees_pipeline"]

    if mode_vue == "Client":
        from pipeline.ui.views.client.synthese_executive import afficher as afficher_vue_client

        afficher_vue_client(donnees)
    else:
        afficher_vue_cuisine(donnees)


if __name__ == "__main__":
    main()
