import html
import re
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import streamlit as st
from decouple import config

from pipeline.pipeline import PipelineAgentX
from pipeline.ui.react_components import render_react_outputs, render_react_summary

def executer_pipeline(path: str) -> dict:
    pipeline = PipelineAgentX()
    return pipeline.run(path)


def appliquer_style_typographique() -> None:
    st.markdown(
        """
        <style>
        h1, h2, h3,
        div[data-testid="stMarkdown"] h1,
        div[data-testid="stMarkdown"] h2,
        div[data-testid="stMarkdown"] h3 {
            font-family: "HK Grotesk", "HKGrotesk", Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
            text-align: center !important;
            letter-spacing: 0 !important;
        }
        div[data-testid="stMarkdown"] h1 {
            font-weight: 800 !important;
        }
        div[data-testid="stMarkdown"] h2,
        div[data-testid="stMarkdown"] h3 {
            font-weight: 760 !important;
        }
        div[data-testid="stButton"] button {
            width: auto !important;
            min-height: 2.15rem !important;
            padding: .35rem .75rem !important;
            border-radius: 8px !important;
            font-weight: 750 !important;
        }
        .px8-screen-block-title {
            color: #64748b;
            font-family: "HK Grotesk", "HKGrotesk", Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: .78rem;
            font-weight: 850;
            line-height: 1.15;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0;
            margin: -.15rem 0 .55rem;
            padding-bottom: .45rem;
            border-bottom: 1px solid #e8edf5;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #e8edf5 !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 8px rgba(15, 23, 42, .045) !important;
        }
        @keyframes px8-red-alert-pulse {
            0%, 49% {
                color: #ffffff;
                background: #dc2626;
                border-color: #dc2626;
            }
            50%, 100% {
                color: #dc2626;
                background: #ffffff;
                border-color: #dc2626;
            }
        }
        .px8-red-alert {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin: .35rem auto .65rem;
            padding: .42rem .78rem;
            border: 1px solid #dc2626;
            border-radius: 8px;
            color: #ffffff;
            background: #dc2626;
            font-weight: 900;
            text-transform: uppercase;
            animation: px8-red-alert-pulse 1s infinite;
        }
        .px8-no-alert {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin: .35rem auto .65rem;
            padding: .42rem .78rem;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            color: #6b7280;
            background: #f8fafc;
            font-weight: 800;
        }
        .px8-main-header-title {
            font-family: "HK Grotesk", "HKGrotesk", Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 1.75rem;
            font-weight: 850;
            line-height: 1.1;
            text-align: center;
            letter-spacing: 0;
            margin: .1rem 0 .3rem;
            color: #172026;
        }
        .px8-main-header-subtitle {
            color: #64717d;
            font-size: .9rem;
            line-height: 1.25;
            text-align: center;
            margin: 0;
        }
        .px8-import-title {
            font-family: "HK Grotesk", "HKGrotesk", Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 2.1rem;
            font-weight: 900;
            line-height: 1;
            text-align: center;
            color: #172026;
            margin: .4rem 0 1.25rem;
        }
        .px8-import-shell {
            border: 1.5px solid #ff9fa5;
            border-radius: 12px;
            background: #fffafa;
            margin: 0 auto 1rem;
            padding: 1.25rem 1.05rem .95rem;
            min-height: 100%;
        }
        .px8-import-bar {
            display: flex;
            align-items: center;
            gap: .9rem;
            padding: .95rem 1.15rem;
            border-bottom: 1px solid #dde2ea;
            background: #f8fafc;
            color: #31333f;
            font-size: 1.18rem;
            font-weight: 800;
        }
        .px8-import-body {
            border: 1.5px solid #ffb3b8;
            border-radius: 10px;
            margin: 1.1rem 0 0;
            padding: 1rem;
            background: #fffafa;
        }
        .px8-import-help {
            color: #85858f;
            font-size: 1.02rem;
            line-height: 1.42;
            margin: 0 0 1.15rem;
        }
        .px8-import-tabs-note {
            color: #64748b;
            font-size: .86rem;
            font-weight: 800;
            text-transform: uppercase;
            margin: .15rem 0 .5rem;
        }
        .px8-import-field-label {
            color: #627088;
            font-family: "HK Grotesk", "HKGrotesk", Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: .86rem;
            font-weight: 900;
            line-height: 1.15;
            text-transform: uppercase;
            margin: 0 0 .7rem;
        }
        .px8-import-source-title {
            color: #627088;
            font-family: "HK Grotesk", "HKGrotesk", Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 1.02rem;
            font-weight: 900;
            line-height: 1.2;
            text-transform: uppercase;
            margin: .25rem 0 1.05rem;
        }
        .px8-upload-frame {
            border: 1.5px solid #ff9fa5;
            border-radius: 12px;
            background: #ffffff;
            padding: .55rem .7rem .15rem;
            margin: .35rem 0 1.2rem;
        }
        .px8-upload-frame [data-testid="stFileUploaderDropzone"] {
            background: #f1f4f8 !important;
            border: 0 !important;
            border-radius: 8px !important;
            min-height: 78px !important;
            padding: .65rem .8rem !important;
        }
        .px8-upload-frame [data-testid="stFileUploaderDropzone"] button {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            color: #31333f !important;
            min-height: 2.6rem !important;
            padding: .45rem 1rem !important;
            font-size: .98rem !important;
            box-shadow: 0 1px 6px rgba(15, 23, 42, .08) !important;
        }
        .px8-upload-frame [data-testid="stFileUploaderDropzone"] small,
        .px8-upload-frame [data-testid="stFileUploaderDropzoneInstructions"] {
            color: #85858f !important;
            font-size: .92rem !important;
        }
        .px8-select-like {
            border: 2px solid #ff4d55;
            border-radius: 10px;
            background: #ffffff;
            color: #31333f;
            font-size: 1rem;
            line-height: 1.2;
            padding: .95rem 1rem;
            margin: .35rem 0 1.3rem;
        }
        .px8-api-frame {
            border: 1.5px solid #ff9fa5;
            border-radius: 12px;
            background: #ffffff;
            padding: 1rem;
            margin: .35rem 0 1.2rem;
        }
        .px8-api-note {
            color: #85858f;
            font-size: .96rem;
            line-height: 1.42;
            margin: .15rem 0 1rem;
        }
        .px8-import-dependency {
            color: #85858f;
            font-size: .92rem;
            margin: .8rem 0 1rem;
        }
        .px8-import-dependency code {
            color: #4f9d69;
            background: #fbfbfb;
            padding: .1rem .25rem;
            border-radius: 6px;
        }
        .px8-source-file-pill {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            max-width: 100%;
            margin: .1rem 0 .75rem;
            padding: .42rem .72rem;
            border-radius: 999px;
            background: #eaf8ee;
            color: #0f7a32;
            font-size: .9rem;
            font-weight: 850;
            line-height: 1.2;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .px8-source-file-pill span {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def bloc_ecran(titre: str):
    with st.container(border=True):
        st.markdown(
            f'<div class="px8-screen-block-title">{html.escape(titre)}</div>',
            unsafe_allow_html=True,
        )
        yield


def afficher_badge_fichier_source(fichier: str) -> None:
    chemin = Path(fichier).resolve()
    try:
        libelle = chemin.relative_to(Path.cwd()).as_posix()
    except ValueError:
        libelle = chemin.name

    st.markdown(
        f'<div class="px8-source-file-pill">↗ <span>Fichier source : {html.escape(libelle)}</span></div>',
        unsafe_allow_html=True,
    )


def afficher_resume(donnees: dict) -> None:
    dataset = donnees.get("dataset")
    historique = donnees.get("historique_modules", [])

    render_react_summary(
        [
            {"label": "Modules executes", "value": len(historique), "tone": "ok"},
            {
                "label": "Lignes dataset",
                "value": len(dataset) if isinstance(dataset, pd.DataFrame) else 0,
            },
            {
                "label": "Arret pipeline",
                "value": "Oui" if donnees.get("arreter_pipeline") else "Non",
                "tone": "warn" if donnees.get("arreter_pipeline") else "ok",
            },
            {"label": "Communautes", "value": len(donnees.get("communautes", []))},
        ]
    )

    if donnees.get("erreur_pipeline"):
        st.error(donnees["erreur_pipeline"])


def afficher_etapes(donnees: dict) -> None:
    historique = donnees.get("historique_modules", [])

    if not historique:
        st.info("Aucun module execute.")
        return

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
    communautes = []
    for communaute in donnees.get("communautes", [])[:8]:
        communautes.append(
            {
                "id": communaute.get("id"),
                "nombre_messages": communaute.get("nombre_messages"),
                "pct_negative": communaute.get("pct_negative"),
                "jour_pic": communaute.get("jour_pic"),
                "sources_pivots": communaute.get("sources_pivots", []),
            }
        )

    render_react_outputs(
        {
            "declencheur": donnees.get("declencheur"),
            "communautes": communautes,
            "proposition": donnees.get("proposition"),
            "arreter_pipeline": donnees.get("arreter_pipeline"),
        }
    )


def valeur_tableau_lisible(valeur):
    if isinstance(valeur, dict):
        return ", ".join(f"{cle}: {valeur_lisible}" for cle, valeur_lisible in valeur.items())

    if isinstance(valeur, (list, tuple, set)):
        elements = []
        for element in valeur:
            if isinstance(element, (list, tuple)) and len(element) >= 2:
                elements.append(f"{element[0]} ({element[1]})")
            else:
                elements.append(str(element))
        return ", ".join(elements)

    return valeur


def dataframe_tableau_lisible(dataframe: pd.DataFrame) -> pd.DataFrame:
    tableau = dataframe.copy()
    colonnes_objet = tableau.select_dtypes(include=["object"]).columns
    for colonne in colonnes_objet:
        tableau[colonne] = tableau[colonne].map(valeur_tableau_lisible)
    return tableau


def expliquer_graphe(question: str, lecture: str) -> None:
    st.markdown(f"**Question humaine :** {question}")
    st.caption(f"Lecture : {lecture}")


def derniere_collecte_lisible(donnees: dict) -> str:
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Date" not in dataset.columns:
        return "Dernière collecte : n/a"

    dates = pd.to_datetime(dataset["Date"], errors="coerce").dropna()
    if dates.empty:
        return "Dernière collecte : n/a"

    derniere_date = dates.max()
    return f"Dernière collecte : {derniere_date:%d/%m/%Y à %H:%M}"


def periode_collecte_lisible(donnees: dict) -> str:
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Date" not in dataset.columns:
        return "Période de collecte : n/a"

    dates = pd.to_datetime(dataset["Date"], errors="coerce").dropna()
    if dates.empty:
        return "Période de collecte : n/a"

    debut = dates.min()
    fin = dates.max()
    return f"Période de collecte : du {debut:%d/%m/%Y à %H:%M} au {fin:%d/%m/%Y à %H:%M}"


def mots_recits_lisibles(donnees: dict) -> str:
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
    mots = []
    for recit in recits[:6]:
        mots_cles = recit.get("mots_cles", [])
        if mots_cles:
            mots.append(str(mots_cles[0]))
        elif recit.get("nom"):
            mots.append(str(recit["nom"]).split(",")[0].strip())
    return " · ".join(mots) if mots else "mots-clés n/a"


def signaux_priorite_lisibles(donnees: dict) -> str:
    signaux = []
    proposition = donnees.get("proposition", {})
    chiffres = proposition.get("chiffres_cles", {}) if isinstance(proposition, dict) else {}
    recit = proposition.get("recit_prioritaire", {}) if isinstance(proposition, dict) else {}

    alerte = etat_alerte_trigger_volume(donnees)
    if alerte["alerte"]:
        signaux.append(f"impressions > seuil ({alerte['messages_au_dessus']:,})")

    top_amplificateurs = chiffres.get("top_amplificateurs") or []
    if top_amplificateurs:
        premier = top_amplificateurs[0]
        source = premier.get("source")
        retweets = premier.get("retweets")
        if source and retweets is not None:
            signaux.append(f"{source}: {retweets:,} RT")

    if recit.get("pct_negative") not in (None, "n/a"):
        signaux.append(f"{recit.get('pct_negative')}% nég.")

    if chiffres.get("top20_share_pct") not in (None, "n/a"):
        signaux.append(f"top 20 RT {chiffres.get('top20_share_pct')}%")

    return " · ".join(signaux[:3]) if signaux else "signaux à qualifier"


def statut_module(donnees: dict, nom_module: str) -> str:
    for trace in donnees.get("historique_modules", []):
        if trace.get("module") == nom_module:
            return str(trace.get("statut", "en attente"))
    return "en attente"


def etat_alerte_trigger_volume(donnees: dict) -> dict:
    seuil = config("SEUIL_IMPRESSION", default=5000, cast=int)
    dataset = donnees.get("dataset")
    messages_au_dessus = 0
    if isinstance(dataset, pd.DataFrame) and "Impressions" in dataset.columns:
        impressions = pd.to_numeric(dataset["Impressions"], errors="coerce").fillna(0)
        messages_au_dessus = int((impressions > seuil).sum())
    return {
        "seuil": seuil,
        "messages_au_dessus": messages_au_dessus,
        "alerte": messages_au_dessus > 0,
        "libelle": "Red Alert" if messages_au_dessus > 0 else "Aucune alerte",
    }


def texte_contrat_mis_en_valeur(texte: str) -> str:
    texte_echappe = html.escape(texte)
    debut, separateur, suite = texte_echappe.partition(":")
    if separateur and len(debut) <= 42:
        texte_echappe = f"<strong>{debut}</strong>{separateur}{suite}"

    mots_importants = [
        "DataFrame",
        "Colonnes attendues",
        "SEUIL_IMPRESSION",
        "SEUIL_MESSAGES_COMMUNAUTE",
        "SEUIL_VIRALITE_HAUT",
        "SEUIL_VIRALITE_MOYEN",
        "TF-IDF",
        "KMeans",
        "Louvain",
        "NetworkX",
        "Gini",
        "NLP",
        "RAG",
        "joblib",
        "predict_proba",
        "Sentiment",
        "Author",
        "Impressions",
        "Engagement Type",
        "X Followers",
        "X Verified",
        "X Posts",
        "Hashtags",
        "Full Text",
        "Date",
        "Reach",
        "Viralite",
        "Classe_viralite",
        "message_normalizer",
        "_source",
        "_status_id",
        "_is_original",
        "volume",
        "négativité",
        "score de risque",
        "récit prioritaire",
        "communautés",
        "sources pivots",
        "validation humaine",
    ]
    for mot in sorted(mots_importants, key=len, reverse=True):
        motif = re.compile(rf"(?<![\w>])({re.escape(html.escape(mot))})(?![\w<])", re.IGNORECASE)
        texte_echappe = motif.sub(r"<strong>\1</strong>", texte_echappe)
    return texte_echappe


def afficher_carte_contrat(titre: str, items: list[str], accent: str) -> None:
    lignes = "".join(
        f"""
        <div style="display: flex; gap: .62rem; align-items: flex-start; margin: 0 0 .5rem;">
            <span style="
                color: {accent};
                font-size: 1.05rem;
                font-weight: 950;
                line-height: 1.25;
                flex: 0 0 auto;
            ">&rarr;</span>
            <span>{texte_contrat_mis_en_valeur(item)}</span>
        </div>
        """
        for item in items
    )
    st.markdown(
        f"""
        <div style="
            padding: .15rem .35rem .4rem;
        ">
            <div style="
                text-align: center;
                font-family: 'HK Grotesk', 'HKGrotesk', Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                color: {accent};
                font-size: .78rem;
                font-weight: 800;
                line-height: 1.2;
                text-transform: uppercase;
                letter-spacing: 0;
                margin: 0 0 .5rem;
            ">{html.escape(titre)}</div>
            <div style="
                min-height: 150px;
                border: 1px solid #e1e8f0;
                border-radius: 8px;
                padding: .78rem .95rem .55rem;
                background: #ffffff;
                box-shadow: 0 1px 8px rgba(15, 23, 42, .04);
                margin: 0;
                color: #31333f;
                line-height: 1.36;
                font-size: .9rem;
                font-weight: 400;
            ">{lignes}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def afficher_contrat_agent(titre: str, axe: str, entree: list[str], calcul: list[str], metriques: dict, sortie: list[str]) -> None:
    st.subheader(titre)
    st.caption(f"Axe datathon couvert : {axe}")
    col_entree, col_calcul, col_sortie = st.columns([1, 1.2, 1])
    with col_entree:
        afficher_carte_contrat("Entrée attendue", entree, "#7db7b2")
    with col_calcul:
        afficher_carte_contrat("Calcul / méthode", calcul, "#4b2e83")
    with col_sortie:
        afficher_carte_contrat("Sortie vers l'agent suivant", sortie, "#ff7a33")

    if metriques:
        st.markdown("**Métriques observées**")
        cols = st.columns(min(4, len(metriques)))
        for col, (label, value) in zip(cols, metriques.items()):
            col.metric(label, value)


def lancer_pipeline_depuis_chemin(chemin: str) -> None:
    with st.spinner("Execution de la pipeline..."):
        st.session_state["donnees_pipeline"] = executer_pipeline(chemin)
        st.session_state["dernier_chemin_pipeline"] = chemin
        st.session_state["pipeline_active_tab"] = "acteurs"
        st.session_state["pipeline_timeline_version"] = st.session_state.get("pipeline_timeline_version", 0) + 1
    st.rerun()


def afficher_source_active() -> None:
    if "donnees_pipeline" not in st.session_state:
        return
    donnees = st.session_state["donnees_pipeline"]
    dataset = donnees.get("dataset")
    if isinstance(dataset, pd.DataFrame):
        st.info(
            "Source active : "
            f"{st.session_state.get('dernier_chemin_pipeline', 'n/a')} · "
            f"{len(dataset):,} lignes"
        )


def afficher_header_principal_avec_toggle() -> str:
    if "mode_vue_principale" not in st.session_state:
        st.session_state["mode_vue_principale"] = "Cuisine"

    mode_actif = st.session_state["mode_vue_principale"]
    if mode_actif == "Client":
        titre = "Synthèse exécutive - Crise informationnelle"
        sous_titre = periode_collecte_lisible(st.session_state.get("donnees_pipeline", {}))
    else:
        titre = "Cuisine agentique - Datathon PX8"
        sous_titre = "De la crise brute aux agents : acteurs, propagation, viralité, coordination, narratifs, sémantique, proposition."

    with st.container(border=True):
        col_gauche, col_titre, col_toggle = st.columns([0.22, 0.56, 0.22], vertical_alignment="center")
        with col_titre:
            st.markdown(
                f"""
                <div class="px8-main-header-title">{html.escape(titre)}</div>
                <p class="px8-main-header-subtitle">{html.escape(sous_titre)}</p>
                """,
                unsafe_allow_html=True,
            )
        with col_toggle:
            col_cuisine, col_client = st.columns(2)
            with col_cuisine:
                if st.button(
                    "Cuisine",
                    type="primary" if st.session_state["mode_vue_principale"] == "Cuisine" else "secondary",
                    key="toggle_vue_cuisine",
                ):
                    st.session_state["mode_vue_principale"] = "Cuisine"
                    st.rerun()
            with col_client:
                if st.button(
                    "Client",
                    type="primary" if st.session_state["mode_vue_principale"] == "Client" else "secondary",
                    key="toggle_vue_client",
                ):
                    st.session_state["mode_vue_principale"] = "Client"
                    st.rerun()

    return st.session_state["mode_vue_principale"]
