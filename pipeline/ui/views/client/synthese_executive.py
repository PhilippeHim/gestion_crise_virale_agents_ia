from pipeline.ui.views.client import (
    diagnostic,
    kpis,
    messages_cles,
    priorite,
    reperes_visuels,
    reponse,
    validation,
)


def afficher(donnees: dict) -> None:
    kpis.afficher(donnees)
    diagnostic.afficher(donnees)
    priorite.afficher(donnees)
    reperes_visuels.afficher(donnees)
    messages_cles.afficher(donnees)
    reponse.afficher(donnees)
    validation.afficher(donnees)
