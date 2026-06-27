from pathlib import Path

import pandas as pd
import streamlit as st

from pipeline.ui.timeline_selector import timeline_selector
from pipeline.ui.view_utils import etat_alerte_trigger_volume, statut_module

def construire_timeline(donnees: dict) -> list[dict]:
    dataset = donnees.get("dataset")
    lignes = len(dataset) if isinstance(dataset, pd.DataFrame) else 0
    communautes = donnees.get("communautes", [])
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []

    return [
        {
            "key": "acteurs",
            "highlight_keys": ["viralite"],
            "label": "Acteurs",
            "value": f"{lignes:,} messages",
            "detail": "Qui parle ? Médias, militants, influenceurs, anonymes, comptes suspects.",
            "filled": lignes > 0,
        },
        {
            "key": "narratifs",
            "label": "Narratifs",
            "value": f"{len(recits)} récits",
            "detail": "Quels discours ? Mots-clés, thèmes discutés, récits structurants.",
            "filled": len(recits) > 0,
        },
        {
            "key": "propagation",
            "highlight_keys": ["declencheurs"],
            "label": "Propagation",
            "value": statut_module(donnees, "Declencheur"),
            "detail": "Comment ça circule ? Patient zéro, pics de volume, vitesse, amplitude.",
            "filled": statut_module(donnees, "Declencheur") == "fait",
        },
        {
            "key": "coordination",
            "label": "Coordination",
            "value": f"{len(communautes)} communautés",
            "detail": "Est-ce orchestré ? Synchronies, copier-coller, comptes récents, clusters.",
            "filled": len(communautes) > 0,
        },
        {
            "key": "semantique",
            "highlight_keys": ["filtre_3"],
            "label": "Sémantique",
            "value": f"{narratif.get('tonalite', {}).get('part_negative', 'n/a')}% nég.",
            "detail": "Sur quel ton ? Sentiment, agressivité, glissements de vocabulaire.",
            "filled": bool(narratif.get("tonalite")),
        },
    ]


def construire_pipeline_px8(donnees: dict) -> list[dict]:
    dataset = donnees.get("dataset")
    lignes = len(dataset) if isinstance(dataset, pd.DataFrame) else 0
    communaute = donnees.get("communaute", {})
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
    proposition = donnees.get("proposition") or {}
    alerte_trigger_1 = etat_alerte_trigger_volume(donnees)

    return [
        {
            "key": "collecte_filtrage",
            "phase": "Collecte & filtrage",
            "label": "Collecte & filtres",
            "value": f"{lignes:,} messages",
            "detail": "XLSX, API/scraping, requête, nettoyage",
            "tone": "blue",
            "filled": lignes > 0,
        },
        {
            "key": "declencheurs",
            "highlight_keys": ["propagation"],
            "phase": "Déclencheurs",
            "label": "Déclencheurs",
            "value": alerte_trigger_1["libelle"],
            "detail": "Volume, impressions, certifiés, concentration",
            "tone": "orange",
            "filled": statut_module(donnees, "Declencheur") == "fait",
        },
        {
            "key": "viralite",
            "highlight_keys": ["acteurs"],
            "phase": "Agents d'analyse",
            "label": "Agent 1",
            "value": "Viralité",
            "detail": "Impressions, likes, shares, commentaires",
            "tone": "green",
            "filled": statut_module(donnees, "AgentViralite") == "fait",
        },
        {
            "key": "coordination",
            "phase": "Agents d'analyse",
            "label": "Communauté",
            "value": f"{len(donnees.get('communautes', []))} communautés",
            "detail": "Louvain, polarisation, certifiés, followers",
            "tone": "green",
            "filled": len(donnees.get("communautes", [])) > 0,
        },
        {
            "key": "narratifs",
            "phase": "Agents d'analyse",
            "label": "Agent 2",
            "value": f"{len(recits)} récits",
            "detail": "Contenu, narratifs, sentiment",
            "tone": "green",
            "filled": len(recits) > 0,
        },
        {
            "key": "propagation",
            "highlight_keys": ["declencheurs"],
            "phase": "Agents d'analyse",
            "label": "Agent 3",
            "value": "Propagation",
            "detail": "Timeline, pics, patient zéro, relais",
            "tone": "green",
            "filled": statut_module(donnees, "Declencheur") == "fait",
        },
        {
            "key": "filtre_3",
            "highlight_keys": ["semantique"],
            "phase": "Script & filtre",
            "label": "Filtre 3",
            "value": "Risque",
            "detail": "Significativité, manipulation, polarisation",
            "tone": "amber",
            "filled": bool(narratif.get("tonalite")) if isinstance(narratif, dict) else False,
        },
        {
            "key": "proposition_finale",
            "highlight_keys": ["proposition"],
            "phase": "Proposition",
            "label": "Proposition",
            "value": proposition.get("priorite", "Décision"),
            "detail": "Reformuler, répondre, valider",
            "tone": "purple",
            "filled": bool(proposition),
        },
    ]


def choisir_vue_timeline(donnees: dict, mode_vide: bool = False) -> str:
    steps = [] if mode_vide else construire_timeline(donnees)
    pipeline_stages = construire_pipeline_px8(donnees)
    if mode_vide:
        pipeline_stages = [
            stage if stage.get("key") == "collecte_filtrage" else {**stage, "key": None, "disabled": True}
            for stage in pipeline_stages
        ]
    tabs = [{"key": step["key"], "label": step["label"]} for step in steps]
    vues_valides = {step["key"] for step in steps} | {stage["key"] for stage in pipeline_stages if stage.get("key")} | {"collecte_filtrage", "declencheurs", "filtre_3", "proposition_finale", "aucun"}
    tab_defaut = "aucun" if mode_vide else "acteurs"
    active_tab = st.session_state.get("pipeline_active_tab", tab_defaut)
    if active_tab not in vues_valides:
        active_tab = tab_defaut
        st.session_state["pipeline_active_tab"] = active_tab
    timeline_version = st.session_state.get("pipeline_timeline_version", 0)
    timeline_mode = "vide" if mode_vide else "charge"
    valeur = timeline_selector(
        steps=steps,
        pipeline_stages=pipeline_stages,
        tabs=tabs,
        active_tab=active_tab,
        dataset_label=Path(str(donnees.get("path") or "Aucune source chargée")).name,
        key=f"pipeline_timeline_navigation_{timeline_mode}_{timeline_version}",
    )
    if isinstance(valeur, dict) and valeur.get("activeTab") in vues_valides:
        next_tab = valeur["activeTab"]
        if next_tab != active_tab:
            st.session_state["pipeline_active_tab"] = next_tab
            st.rerun()
    return st.session_state.get("pipeline_active_tab", active_tab)
