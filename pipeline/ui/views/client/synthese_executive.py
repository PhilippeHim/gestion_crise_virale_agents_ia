import streamlit as st

from pipeline.ui.charts import graphique_sentiment_journalier, graphique_volume_journalier
from pipeline.ui.react_components import render_crisis_dashboard


def afficher(donnees: dict) -> None:
    """Vue client principale - Crisis Intelligence Center."""
    render_crisis_dashboard(donnees, height=920)

    st.subheader("Repères visuels")
    col_volume, col_tonalite = st.columns(2)

    with col_volume:
        fig_volume = graphique_volume_journalier(donnees)
        if fig_volume is not None:
            st.plotly_chart(fig_volume, use_container_width=True)
            with st.expander("Agrandir le volume quotidien"):
                fig_large = graphique_volume_journalier(donnees)
                if fig_large is not None:
                    fig_large.update_layout(height=520)
                    st.plotly_chart(fig_large, use_container_width=True)
        else:
            st.info("Volume quotidien indisponible.")

    with col_tonalite:
        fig_tonalite = graphique_sentiment_journalier(donnees)
        if fig_tonalite is not None:
            st.plotly_chart(fig_tonalite, use_container_width=True)
            with st.expander("Agrandir la tonalité au fil du temps"):
                fig_large = graphique_sentiment_journalier(donnees)
                if fig_large is not None:
                    fig_large.update_layout(height=520)
                    st.plotly_chart(fig_large, use_container_width=True)
        else:
            st.info("Tonalité au fil du temps indisponible.")
