import streamlit as st

from pipeline.ui.charts import graphique_recits, graphique_volume_journalier


def afficher(donnees: dict) -> None:
    st.subheader("Repères visuels")
    fig_volume = graphique_volume_journalier(donnees)
    fig_recits = graphique_recits(donnees)
    graph_col1, graph_col2 = st.columns(2)
    with graph_col1:
        if fig_volume is not None:
            st.plotly_chart(fig_volume, use_container_width=True)
            with st.expander("Agrandir le volume quotidien"):
                fig_large = graphique_volume_journalier(donnees)
                if fig_large is not None:
                    fig_large.update_layout(height=520)
                    st.plotly_chart(fig_large, use_container_width=True)
    with graph_col2:
        if fig_recits is not None:
            st.plotly_chart(fig_recits, use_container_width=True)
            with st.expander("Agrandir les récits"):
                fig_large = graphique_recits(donnees)
                if fig_large is not None:
                    fig_large.update_layout(height=560)
                    st.plotly_chart(fig_large, use_container_width=True)
