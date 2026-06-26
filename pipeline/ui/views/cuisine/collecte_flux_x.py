from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *

def afficher(donnees: dict | None = None) -> None:
    afficher_badge_fichier_source(__file__)
    st.markdown('<div class="px8-import-title">Collecte & filtrage</div>', unsafe_allow_html=True)
    col_xlsx, col_scraping = st.columns(2, gap="large")

    with col_xlsx:
        st.markdown(
            """
            <div class="px8-import-shell">
                <div class="px8-import-field-label">Source</div>
                <div class="px8-import-source-title">Importer un dataset XLSX</div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="px8-upload-frame">', unsafe_allow_html=True)
        fichier = st.file_uploader(
            "Fichier .xlsx",
            type=["xlsx"],
            key="flux_x_fichier_excel",
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            '<p class="px8-import-dependency">Entrée attendue : <code>.xlsx</code> avec auteurs, texte, dates, impressions et engagements.</p>',
            unsafe_allow_html=True,
        )

        if st.button("Lancer la collecte depuis ce fichier", type="primary", disabled=fichier is None):
            suffixe = Path(fichier.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffixe) as tmp:
                tmp.write(fichier.getbuffer())
                lancer_pipeline_depuis_chemin(tmp.name)
            st.success("Pipeline exécutée depuis le fichier uploadé.")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_scraping:
        st.markdown(
            """
            <div class="px8-import-shell">
                <div class="px8-import-field-label">Collecte X</div>
                <div class="px8-import-source-title">API / scraping X</div>
                <div class="px8-api-frame">
                    <p class="px8-api-note">
                        Préparer la collecte directe du flux X : mode de récupération, volume maximal,
                        requête et sortie normalisée avant filtres.
                    </p>
            """,
            unsafe_allow_html=True,
        )

        mode_collecte = st.selectbox(
            "Mode de collecte",
            ["Search API", "Stream API", "Scraping contrôlé"],
            key="flux_x_mode_collecte",
        )
        requete = st.text_input(
            "Requête",
            value='("CNC" OR "CNC Talent" OR "Ultia") lang:fr',
            key="flux_x_requete_collecte",
        )
        volume_max = st.number_input(
            "Volume maximal",
            min_value=100,
            max_value=500000,
            value=50000,
            step=1000,
            key="flux_x_volume_max",
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            '<p class="px8-import-dependency">À brancher : <code>credentials</code>, pagination, limites d’usage, normalisation et stockage brut.</p>',
            unsafe_allow_html=True,
        )
        st.json(
            {
                "mode": mode_collecte,
                "requete": requete,
                "volume_max": int(volume_max),
                "sortie": "tweets bruts normalisés avant filtres",
            }
        )
        st.markdown("</div>", unsafe_allow_html=True)

    afficher_source_active()

    st.markdown('<div class="px8-import-title">Filtres de préparation</div>', unsafe_allow_html=True)
    col_filtre_1, col_filtre_2 = st.columns(2, gap="large")

    with col_filtre_1:
        st.markdown(
            """
            <div class="px8-import-shell">
                <div class="px8-import-field-label">Filtre 1</div>
                <div class="px8-import-source-title">Requête, mots-clés & ciblage</div>
                <div class="px8-api-frame">
            """,
            unsafe_allow_html=True,
        )
        requete_filtre = st.text_input(
            "Requête X",
            value='("CNC" OR "CNC Talent" OR "Ultia") lang:fr',
            key="filtre_1_requete",
        )
        hashtags = st.text_input("Hashtags", value="#CNC,#CNCTalent,#Ultia", key="filtre_1_hashtags")
        comptes = st.text_area(
            "Comptes / origines",
            value="ultia\noffinvestigatio\ncharlesvillaa",
            height=120,
            key="filtre_1_comptes",
        )
        langue = st.selectbox("Langue", ["fr", "en", "all"], key="filtre_1_langue")
        st.markdown("</div>", unsafe_allow_html=True)
        filtre_1_config = {
            "requete": requete_filtre,
            "hashtags": [tag.strip() for tag in hashtags.split(",") if tag.strip()],
            "comptes": [ligne.strip() for ligne in comptes.splitlines() if ligne.strip()],
            "langue": langue,
            "sortie": "tweets bruts filtrés par périmètre de crise",
        }
        if st.button("Valider le filtre 1", type="primary"):
            st.session_state["filtre_1_config"] = filtre_1_config
            st.success("Filtre 1 enregistré.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_filtre_2:
        st.markdown(
            """
            <div class="px8-import-shell">
                <div class="px8-import-field-label">Filtre 2</div>
                <div class="px8-import-source-title">Nettoyage & enrichissement</div>
                <div class="px8-api-frame">
            """,
            unsafe_allow_html=True,
        )
        dedoublonner = st.checkbox("Supprimer les doublons textuels", value=True, key="filtre_2_dedoublonner")
        inclure_retweets = st.checkbox("Conserver les retweets / reposts", value=True, key="filtre_2_retweets")
        enrichir_sources = st.checkbox("Extraire _source et _status_id", value=True, key="filtre_2_sources")
        normaliser_texte = st.checkbox("Normaliser le texte pour NLP", value=True, key="filtre_2_normaliser")
        st.markdown("</div>", unsafe_allow_html=True)
        filtre_2_config = {
            "dedoublonner": bool(dedoublonner),
            "inclure_retweets": bool(inclure_retweets),
            "enrichir_sources": bool(enrichir_sources),
            "normaliser_texte": bool(normaliser_texte),
            "sortie": "DataFrame compatible avec ChargementDataset et agents PX8",
        }
        if st.button("Valider le filtre 2", type="primary"):
            st.session_state["filtre_2_config"] = filtre_2_config
            st.success("Filtre 2 enregistré.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="px8-import-shell">
            <div class="px8-import-field-label">Contrat</div>
            <div class="px8-import-source-title">Collecte & filtres</div>
        """,
        unsafe_allow_html=True,
    )
    col_contrat_1, col_contrat_2 = st.columns(2)
    with col_contrat_1:
        st.json(st.session_state.get("filtre_1_config", filtre_1_config))
    with col_contrat_2:
        st.json(st.session_state.get("filtre_2_config", filtre_2_config))
    st.markdown("</div>", unsafe_allow_html=True)
