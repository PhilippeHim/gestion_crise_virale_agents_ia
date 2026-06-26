from pipeline.ui.navigation import choisir_vue_timeline
from pipeline.ui.react_components import render_react_header
from pipeline.ui.views.cuisine import (
    acteurs,
    collecte_flux_x,
    coordination,
    declencheurs,
    filtre_risque,
    narratifs,
    propagation,
    proposition,
    proposition_finale,
    semantique,
    viralite,
)


VUES_CUISINE = {
    "collecte_filtrage": collecte_flux_x.afficher,
    "declencheurs": declencheurs.afficher,
    "acteurs": acteurs.afficher,
    "propagation": propagation.afficher,
    "viralite": viralite.afficher,
    "coordination": coordination.afficher,
    "narratifs": narratifs.afficher,
    "filtre_3": filtre_risque.afficher,
    "semantique": semantique.afficher,
    "proposition_finale": proposition_finale.afficher,
    "proposition": proposition.afficher,
}


def afficher_vue_vide() -> None:
    render_react_header(
        "Cuisine agentique - Datathon PX8",
        "De la crise brute aux agents : acteurs, propagation, viralité, coordination, narratifs, sémantique, proposition.",
    )
    vue_active = choisir_vue_timeline({}, mode_vide=True)
    vue = VUES_CUISINE.get(vue_active)
    if vue is not None:
        vue({})


def afficher_vue_cuisine(donnees: dict) -> None:
    vue_active = choisir_vue_timeline(donnees)
    vue = VUES_CUISINE.get(vue_active)
    if vue is not None:
        vue(donnees)
