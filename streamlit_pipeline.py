import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from pipeline.pipeline import PipelineAgentX


st.set_page_config(page_title="Pipeline Agent X", layout="wide")


def executer_pipeline(path: str) -> dict:
    pipeline = PipelineAgentX()
    return pipeline.run(path)


def afficher_resume(donnees: dict) -> None:
    dataset = donnees.get("dataset")
    historique = donnees.get("historique_modules", [])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Modules executes", len(historique))
    col2.metric("Lignes dataset", len(dataset) if isinstance(dataset, pd.DataFrame) else 0)
    col3.metric("Arret pipeline", "Oui" if donnees.get("arreter_pipeline") else "Non")
    col4.metric("Communautes", len(donnees.get("communautes", [])))

    if donnees.get("erreur_pipeline"):
        st.error(donnees["erreur_pipeline"])


def afficher_etapes(donnees: dict) -> None:
    historique = donnees.get("historique_modules", [])

    if not historique:
        st.info("Aucun module execute.")
        return

    colonnes = st.columns(len(historique))
    for colonne, trace in zip(colonnes, historique):
        statut = trace["statut"]
        if statut == "fait":
            colonne.success(trace["module"])
        elif statut == "erreur":
            colonne.error(trace["module"])
        else:
            colonne.info(trace["module"])
        colonne.caption(statut)

    st.dataframe(pd.DataFrame(historique), use_container_width=True, hide_index=True)


def afficher_dataset(donnees: dict) -> None:
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame):
        st.info("Dataset non charge.")
        return

    st.subheader("Exploration")

    col1, col2, col3 = st.columns([1, 1, 1])
    auteur = col1.text_input("Auteur", placeholder="ex: destinationcine")
    mot_cle = col2.text_input("Mot cle", placeholder="ex: CNC")
    masquer_retweets = col3.checkbox("Masquer les retweets", value=False)

    dataset_affiche = dataset.copy()

    if auteur and "Author" in dataset_affiche.columns:
        dataset_affiche = dataset_affiche[
            dataset_affiche["Author"].astype(str).str.contains(auteur, case=False, na=False)
        ]

    if mot_cle:
        colonnes_texte = [
            colonne
            for colonne in ["Full Text", "message_normalizer", "Hashtags", "Mentioned Authors"]
            if colonne in dataset_affiche.columns
        ]
        if colonnes_texte:
            masque_mot_cle = pd.Series(False, index=dataset_affiche.index)
            for colonne in colonnes_texte:
                masque_mot_cle = masque_mot_cle | dataset_affiche[colonne].astype(str).str.contains(
                    mot_cle,
                    case=False,
                    na=False,
                )
            dataset_affiche = dataset_affiche[masque_mot_cle]

    if masquer_retweets and "Engagement Type" in dataset_affiche.columns:
        dataset_affiche = dataset_affiche[dataset_affiche["Engagement Type"] != "RETWEET"]

    st.caption(f"{len(dataset_affiche):,} ligne(s) affichee(s) sur {len(dataset):,}")

    colonnes_prioritaires = [
        "Date",
        "Author",
        "Engagement Type",
        "Sentiment",
        "Impressions",
        "Likes",
        "Comments",
        "Shares",
        "Full Text",
        "Hashtags",
    ]
    colonnes_affichees = [
        colonne for colonne in colonnes_prioritaires if colonne in dataset_affiche.columns
    ]

    st.dataframe(dataset_affiche[colonnes_affichees].head(200), use_container_width=True)

    st.subheader("Colonnes")
    colonnes = pd.DataFrame(
        {
            "colonne": dataset.columns,
            "type": [str(dtype) for dtype in dataset.dtypes],
            "valeurs_nulles": dataset.isna().sum().values,
        }
    )
    st.dataframe(colonnes, use_container_width=True, hide_index=True)


def afficher_declencheur(donnees: dict) -> None:
    concentration = donnees.get("concentration")
    amplificateurs = donnees.get("amplificateurs")

    if concentration:
        st.json(concentration)

    graphique_gini = donnees.get("graphique_gini")
    if graphique_gini is not None:
        st.plotly_chart(graphique_gini, use_container_width=True)

    graphique_amplificateurs = donnees.get("graphique_amplificateurs")
    if graphique_amplificateurs is not None:
        st.plotly_chart(graphique_amplificateurs, use_container_width=True)

    if isinstance(amplificateurs, pd.DataFrame):
        st.subheader("Amplificateurs")
        st.dataframe(amplificateurs.head(20), use_container_width=True, hide_index=True)


def afficher_viralite(donnees: dict) -> None:
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame):
        st.info("Dataset non charge.")
        return

    colonnes = [col for col in ["Viralite", "Classe_viralite"] if col in dataset.columns]
    if not colonnes:
        st.info("L'agent de viralite n'a pas encore produit de colonnes.")
        return

    if "Classe_viralite" in dataset.columns:
        st.bar_chart(dataset["Classe_viralite"].value_counts())

    colonnes_apercu = [col for col in ["Full Text", *colonnes] if col in dataset.columns]
    st.dataframe(dataset[colonnes_apercu].head(25), use_container_width=True)


def afficher_sorties(donnees: dict) -> None:
    st.json(
        {
            "declencheur": donnees.get("declencheur"),
            "communautes": donnees.get("communautes"),
            "proposition": donnees.get("proposition"),
            "arreter_pipeline": donnees.get("arreter_pipeline"),
        }
    )


st.title("Visualisation de la pipeline")

with st.sidebar:
    st.header("Entree")
    fichier = st.file_uploader("Dataset Excel", type=["xlsx"])
    chemin_defaut = st.text_input("Ou chemin local", value="data_source/data.xlsx")
    lancer = st.button("Lancer la pipeline", type="primary", use_container_width=True)

if lancer:
    if fichier is not None:
        suffixe = Path(fichier.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffixe) as tmp:
            tmp.write(fichier.getbuffer())
            chemin = tmp.name
    else:
        chemin = chemin_defaut

    with st.spinner("Execution de la pipeline..."):
        st.session_state["donnees_pipeline"] = executer_pipeline(chemin)

if "donnees_pipeline" not in st.session_state:
    st.info("Charge un fichier ou utilise le chemin local, puis lance la pipeline.")
    st.stop()

donnees = st.session_state["donnees_pipeline"]

afficher_resume(donnees)

onglet_etapes, onglet_dataset, onglet_declencheur, onglet_viralite, onglet_sorties = st.tabs(
    ["Etapes", "Dataset", "Declencheur", "Viralite", "Sorties"]
)

with onglet_etapes:
    afficher_etapes(donnees)

with onglet_dataset:
    afficher_dataset(donnees)

with onglet_declencheur:
    afficher_declencheur(donnees)

with onglet_viralite:
    afficher_viralite(donnees)

with onglet_sorties:
    afficher_sorties(donnees)
