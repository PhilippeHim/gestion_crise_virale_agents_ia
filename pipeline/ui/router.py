from importlib import import_module

from pipeline.ui.navigation import choisir_vue_timeline
import streamlit as st


VUES_CUISINE = {
    "collecte_filtrage": "pipeline.ui.views.cuisine.collecte_flux_x",
    "declencheurs": "pipeline.ui.views.cuisine.declencheurs",
    "acteurs": "pipeline.ui.views.cuisine.acteurs",
    "propagation": "pipeline.ui.views.cuisine.propagation",
    "viralite": "pipeline.ui.views.cuisine.viralite",
    "coordination": "pipeline.ui.views.cuisine.coordination",
    "narratifs": "pipeline.ui.views.cuisine.narratifs",
    "filtre_3": "pipeline.ui.views.cuisine.filtre_risque",
    "semantique": "pipeline.ui.views.cuisine.semantique",
    "proposition_finale": "pipeline.ui.views.cuisine.proposition_finale",
    "proposition": "pipeline.ui.views.cuisine.proposition",
}


def afficher_vue(vue_active: str, donnees: dict) -> None:
    module_path = VUES_CUISINE.get(vue_active)
    if module_path is None:
        return
    import_module(module_path).afficher(donnees)


def afficher_vue_vide() -> None:
    st.markdown(
        "<h1 style='text-align:center;margin-bottom:4px'>Cuisine Agent - NACHOS</h1>"
        "<p style='text-align:center;color:#64717d;margin-top:0'>"
        "Neutralisation Agent for Crisis - Human-in-the-loop Orchestration System</p>",
        unsafe_allow_html=True,
    )
    vue_active = choisir_vue_timeline({}, mode_vide=True)
    afficher_vue(vue_active, {})


def afficher_vue_cuisine(donnees: dict) -> None:
    vue_active = choisir_vue_timeline(donnees)
    afficher_vue(vue_active, donnees)
