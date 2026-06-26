import html
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from decouple import config

from pipeline.pipeline import PipelineAgentX
from pipeline.ui.react_components import (
    render_react_header,
    render_react_outputs,
    render_react_summary,
)
from pipeline.ui.timeline_selector import timeline_selector


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
            overflow: hidden;
            margin: 0 auto .95rem;
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
            margin: 1.35rem;
            padding: 1.35rem 1.55rem 1.55rem;
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


def graphique_volume_journalier(donnees: dict):
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Date" not in dataset.columns:
        return None

    base = dataset.copy()
    base["Date"] = pd.to_datetime(base["Date"], errors="coerce")
    base = base.dropna(subset=["Date"])
    if base.empty:
        return None

    quotidien = base.set_index("Date").resample("D").size().reset_index(name="messages")
    fig = px.area(
        quotidien,
        x="Date",
        y="messages",
        title="Volume quotidien de messages",
    )
    fig.update_traces(line_color="#4b2e83", fillcolor="rgba(75, 46, 131, 0.22)")
    fig.update_layout(
        height=250,
        margin=dict(l=8, r=8, t=38, b=8),
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Messages",
    )
    return fig


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


def graphique_top_auteurs(donnees: dict):
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Author" not in dataset.columns:
        return None

    top = dataset["Author"].fillna("inconnu").value_counts().head(15).reset_index()
    top.columns = ["Auteur", "Messages"]
    fig = px.bar(
        top.sort_values("Messages"),
        x="Messages",
        y="Auteur",
        orientation="h",
        title="Auteurs les plus actifs",
        color="Messages",
        color_continuous_scale=["#7db7b2", "#4b2e83"],
    )
    fig.update_layout(height=360, margin=dict(l=8, r=8, t=38, b=8), yaxis_title=None)
    return fig


def graphique_types_engagement(donnees: dict):
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Engagement Type" not in dataset.columns:
        return None

    repartition = dataset["Engagement Type"].fillna("ORIGINAL").value_counts().reset_index()
    repartition.columns = ["Type", "Messages"]
    fig = px.pie(
        repartition,
        names="Type",
        values="Messages",
        title="Nature des messages",
        hole=0.45,
        color_discrete_sequence=["#4b2e83", "#ff7a33", "#7db7b2", "#6b7280"],
    )
    fig.update_layout(height=330, margin=dict(l=8, r=8, t=38, b=8))
    return fig


def graphique_sentiment_journalier(donnees: dict):
    dataset = donnees.get("dataset")
    if (
        not isinstance(dataset, pd.DataFrame)
        or dataset.empty
        or "Date" not in dataset.columns
        or "Sentiment" not in dataset.columns
    ):
        return None

    base = dataset.copy()
    base["Date"] = pd.to_datetime(base["Date"], errors="coerce").dt.date
    base = base.dropna(subset=["Date"])
    if base.empty:
        return None

    quotidien = base.groupby(["Date", "Sentiment"]).size().reset_index(name="Messages")
    fig = px.area(
        quotidien,
        x="Date",
        y="Messages",
        color="Sentiment",
        title="Tonalité au fil du temps",
        color_discrete_map={"negative": "#ff7a33", "neutral": "#4b2e83", "positive": "#7db7b2"},
    )
    fig.update_layout(height=330, margin=dict(l=8, r=8, t=38, b=8), xaxis_title=None)
    return fig


def graphique_viralite_distribution(donnees: dict):
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Classe_viralite" not in dataset.columns:
        return None

    repartition = dataset["Classe_viralite"].fillna("Non classé").value_counts().reset_index()
    repartition.columns = ["Classe", "Messages"]
    fig = px.bar(
        repartition,
        x="Classe",
        y="Messages",
        title="Répartition des classes de viralité",
        color="Classe",
        color_discrete_sequence=["#4b2e83", "#7db7b2", "#ff7a33"],
    )
    fig.update_layout(height=320, margin=dict(l=8, r=8, t=38, b=8), showlegend=False)
    return fig


def graphique_viralite_reach(donnees: dict):
    dataset = donnees.get("dataset")
    colonnes = {"Viralite", "Reach", "X Followers", "Classe_viralite"}
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or not colonnes.issubset(dataset.columns):
        return None

    base = dataset[list(colonnes)].dropna().copy()
    if base.empty:
        return None
    base = base.sort_values("Reach", ascending=False).head(1200)
    fig = px.scatter(
        base,
        x="X Followers",
        y="Reach",
        color="Classe_viralite",
        size="Viralite",
        title="Audience potentielle vs score de viralité",
        color_discrete_map={
            "Non Viral": "#7db7b2",
            "Moyennement Viral": "#4b2e83",
            "Viral": "#ff7a33",
        },
    )
    fig.update_layout(height=360, margin=dict(l=8, r=8, t=38, b=8))
    return fig


def dataframe_communautes(donnees: dict) -> pd.DataFrame:
    communautes = donnees.get("communautes", [])
    if not communautes:
        return pd.DataFrame()
    table = pd.DataFrame(communautes).drop(columns=["narratif"], errors="ignore")
    if "sources_pivots" in table.columns:
        table["sources_lisibles"] = table["sources_pivots"].map(valeur_tableau_lisible)
    return table


def graphique_communautes_risque(donnees: dict):
    table = dataframe_communautes(donnees)
    colonnes = {"nombre_messages", "pct_negative", "nombre_retweeteurs", "pct_verified"}
    if table.empty or not colonnes.issubset(table.columns):
        return None

    fig = px.scatter(
        table,
        x="nombre_messages",
        y="pct_negative",
        size="nombre_retweeteurs",
        color="pct_verified",
        hover_name="id",
        hover_data=["jour_pic", "sources_lisibles"],
        title="Communautés : volume, négativité et comptes vérifiés",
        color_continuous_scale=["#7db7b2", "#ff7a33"],
    )
    fig.update_layout(
        height=380,
        margin=dict(l=8, r=8, t=38, b=8),
        xaxis_title="Messages retweetés",
        yaxis_title="% négatif",
        coloraxis_colorbar_title="% vérifiés",
    )
    return fig


def graphique_sources_pivots(donnees: dict):
    lignes = []
    for communaute in donnees.get("communautes", []):
        for source, volume in communaute.get("sources_pivots", []):
            lignes.append({"Source": source, "Retweets": volume, "Communauté": str(communaute.get("id"))})
    if not lignes:
        return None

    table = pd.DataFrame(lignes).sort_values("Retweets", ascending=False).head(15)
    fig = px.bar(
        table.sort_values("Retweets"),
        x="Retweets",
        y="Source",
        color="Communauté",
        orientation="h",
        title="Sources pivots amplifiées par les communautés",
        color_discrete_sequence=["#4b2e83", "#ff7a33", "#7db7b2", "#6b7280"],
    )
    fig.update_layout(height=380, margin=dict(l=8, r=8, t=38, b=8), yaxis_title=None)
    return fig


def graphique_recits(donnees: dict):
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
    if not recits:
        return None

    df = pd.DataFrame(recits).head(6)
    if df.empty or not {"nom", "volume", "pct_negative"}.issubset(df.columns):
        return None

    fig = px.bar(
        df.sort_values("volume"),
        x="volume",
        y="nom",
        orientation="h",
        color="pct_negative",
        color_continuous_scale=["#4b2e83", "#ff7a33"],
        title="Récits prioritaires : volume et négativité",
    )
    fig.update_layout(
        height=280,
        margin=dict(l=8, r=8, t=38, b=8),
        xaxis_title="Volume",
        yaxis_title=None,
        coloraxis_colorbar_title="% nég.",
    )
    return fig


def graphique_recits_risque(donnees: dict):
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
    if not recits:
        return None

    df = pd.DataFrame(recits)
    colonnes = {"nom", "volume", "pct_negative", "score_risque", "niveau_risque"}
    if df.empty or not colonnes.issubset(df.columns):
        return None

    fig = px.scatter(
        df,
        x="volume",
        y="pct_negative",
        size="score_risque",
        color="niveau_risque",
        hover_name="nom",
        title="Carte des récits : visibilité vs agressivité",
        color_discrete_map={"faible": "#7db7b2", "moyen": "#4b2e83", "eleve": "#ff7a33"},
    )
    fig.update_layout(
        height=380,
        margin=dict(l=8, r=8, t=38, b=8),
        xaxis_title="Volume de messages",
        yaxis_title="% négatif",
    )
    return fig


def graphique_corpus_doublons(donnees: dict):
    narratif = donnees.get("narratif", {})
    corpus = narratif.get("corpus", {}) if isinstance(narratif, dict) else {}
    if not corpus:
        return None

    table = pd.DataFrame(
        [
            {"Étape": "Corpus reçu", "Messages": corpus.get("messages_total", 0)},
            {"Étape": "Textes uniques analysés", "Messages": corpus.get("messages_analyses", 0)},
            {"Étape": "Doublons ignorés pour le NLP", "Messages": corpus.get("messages_ignores_car_doublons", 0)},
        ]
    )
    fig = px.bar(
        table,
        x="Étape",
        y="Messages",
        title="Ce que l'agent NLP garde pour comprendre les récits",
        color="Étape",
        color_discrete_sequence=["#4b2e83", "#7db7b2", "#ff7a33"],
    )
    fig.update_layout(height=320, margin=dict(l=8, r=8, t=38, b=8), showlegend=False)
    return fig


def graphique_sentiment_global(donnees: dict):
    tonalite = donnees.get("narratif", {}).get("tonalite", {})
    repartition = tonalite.get("repartition", {}) if isinstance(tonalite, dict) else {}
    if not repartition:
        return None

    table = pd.DataFrame({"Sentiment": list(repartition.keys()), "Messages": list(repartition.values())})
    fig = px.pie(
        table,
        names="Sentiment",
        values="Messages",
        title="Répartition globale des sentiments",
        hole=0.45,
        color="Sentiment",
        color_discrete_map={"negative": "#ff7a33", "neutral": "#4b2e83", "positive": "#7db7b2"},
    )
    fig.update_layout(height=330, margin=dict(l=8, r=8, t=38, b=8))
    return fig


def afficher_vue_client(donnees: dict) -> None:
    proposition = donnees.get("proposition") or {}
    chiffres = proposition.get("chiffres_cles", {})
    recit_prioritaire = proposition.get("recit_prioritaire", {})

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Messages analysés", f"{chiffres.get('messages_analyses', 0):,}", derniere_collecte_lisible(donnees))
    pic = chiffres.get("pic", {})
    col2.metric("Pic maximal", f"{pic.get('messages', 0):,}", pic.get("date", "n/a"))
    col3.metric("Récits structurants", chiffres.get("nombre_recits", 0), mots_recits_lisibles(donnees))
    col4.metric("Priorité", proposition.get("priorite", "n/a"), signaux_priorite_lisibles(donnees))

    st.subheader("Diagnostic")
    st.write(proposition.get("synthese_executive", "Synthèse non disponible."))

    diagnostic = proposition.get("diagnostic", [])
    if diagnostic:
        for point in diagnostic:
            st.write(f"- {point}")

    st.subheader("Priorité de communication")
    gauche, droite = st.columns([1.2, 1])
    with gauche:
        st.markdown(f"**Stratégie recommandée :** {proposition.get('strategie', 'n/a')}")
        st.markdown(f"**Délai recommandé :** {proposition.get('delai_recommande', 'n/a')}")
        st.markdown(f"**Niveau de risque :** {proposition.get('niveau_risque', 'n/a')}")
        if recit_prioritaire:
            st.markdown(f"**Récit à traiter en priorité :** {recit_prioritaire.get('nom', 'n/a')}")
            st.caption(
                f"Volume {recit_prioritaire.get('volume', 'n/a')} · "
                f"{recit_prioritaire.get('pct_negative', 'n/a')}% négatif · "
                f"score risque {recit_prioritaire.get('score_risque', 'n/a')}"
            )
    with droite:
        st.info(proposition.get("notice_validation", "Validation humaine obligatoire."))

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

    st.subheader("Messages clés")
    for message in proposition.get("messages_cles", []):
        st.write(f"- {message}")

    st.subheader("Brouillon de réponse")
    st.text_area(
        "Texte de travail",
        value=proposition.get("reponse_brouillon", ""),
        height=180,
    )

    col_eviter, col_valider = st.columns(2)
    with col_eviter:
        st.subheader("À éviter")
        for item in proposition.get("messages_a_eviter", []):
            st.write(f"- {item}")
    with col_valider:
        st.subheader("À valider")
        for item in proposition.get("points_a_valider", []):
            st.write(f"- {item}")


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


def construire_timeline(donnees: dict) -> list[dict]:
    dataset = donnees.get("dataset")
    lignes = len(dataset) if isinstance(dataset, pd.DataFrame) else 0
    communautes = donnees.get("communautes", [])
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []

    return [
        {
            "key": "acteurs",
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
            "highlight_keys": ["declencheur_1", "declencheur_2"],
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
            "highlight_keys": ["script_1", "filtre_3"],
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
            "key": "flux_x",
            "phase": "Collecte & filtrage",
            "label": "Flux X",
            "value": f"{lignes:,} messages",
            "detail": "Stream / Search API",
            "tone": "blue",
            "filled": lignes > 0,
        },
        {
            "key": "filtre_1",
            "phase": "Collecte & filtrage",
            "label": "Filtre 1",
            "value": "Requête",
            "detail": "Auteur, origine, mots-clés, hashtags",
            "tone": "blue",
            "filled": lignes > 0,
        },
        {
            "key": "filtre_2",
            "phase": "Collecte & filtrage",
            "label": "Filtre 2",
            "value": "Nettoyage",
            "detail": "Langue, doublons, retweets, métadonnées",
            "tone": "blue",
            "filled": lignes > 0,
        },
        {
            "key": "declencheur_1",
            "highlight_keys": ["propagation"],
            "phase": "Déclencheurs",
            "label": "Trigger 1",
            "value": alerte_trigger_1["libelle"],
            "detail": "Volume, impressions, seuil d'alerte",
            "tone": "orange",
            "filled": statut_module(donnees, "Declencheur") == "fait",
        },
        {
            "key": "declencheur_2",
            "highlight_keys": ["propagation"],
            "phase": "Déclencheurs",
            "label": "Trigger 2",
            "value": "Significativité",
            "detail": "Comptes uniques, certifiés, cumulés",
            "tone": "orange",
            "filled": statut_module(donnees, "Declencheur") == "fait",
        },
        {
            "key": "viralite",
            "phase": "Agents d'analyse",
            "label": "Agent 1",
            "value": "Viralité",
            "detail": "Impressions, likes, shares, commentaires",
            "tone": "green",
            "filled": statut_module(donnees, "AgentViralite") == "fait",
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
            "highlight_keys": ["declencheur_1", "declencheur_2"],
            "phase": "Agents d'analyse",
            "label": "Agent 3",
            "value": "Propagation",
            "detail": "Timeline, pics, patient zéro, relais",
            "tone": "green",
            "filled": statut_module(donnees, "Declencheur") == "fait",
        },
        {
            "key": "coordination",
            "phase": "Agents d'analyse",
            "label": "Agent 2 bis",
            "value": f"{len(donnees.get('communautes', []))} communautés",
            "detail": "Communautés, polarisation, graphes",
            "tone": "green",
            "filled": len(donnees.get("communautes", [])) > 0,
        },
        {
            "key": "script_1",
            "highlight_keys": ["semantique"],
            "phase": "Script & filtre",
            "label": "Script 1",
            "value": "Significativité",
            "detail": "Comptes, certifiés, followers",
            "tone": "amber",
            "filled": bool(narratif.get("tonalite")) if isinstance(narratif, dict) else False,
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
            "key": "proposition_reformulation",
            "highlight_keys": ["proposition", "proposition_reponse", "proposition_validation"],
            "phase": "Proposition",
            "label": "Agent 3",
            "value": "Reformulation",
            "detail": "Formulation et proposition ajustée",
            "tone": "pink",
            "filled": bool(proposition),
        },
        {
            "key": "proposition_reponse",
            "highlight_keys": ["proposition", "proposition_reformulation", "proposition_validation"],
            "phase": "Proposition",
            "label": "Proposition",
            "value": "Réponse",
            "detail": "Réponse générée par Agent 3",
            "tone": "neutral",
            "filled": bool(proposition),
        },
        {
            "key": "proposition_validation",
            "highlight_keys": ["proposition", "proposition_reformulation", "proposition_reponse"],
            "phase": "Décision",
            "label": "Validation",
            "value": proposition.get("priorite", "Décision"),
            "detail": "Publier, modifier ou ignorer",
            "tone": "purple",
            "filled": bool(proposition),
        },
    ]


def choisir_vue_timeline(donnees: dict, mode_vide: bool = False) -> str:
    steps = [] if mode_vide else construire_timeline(donnees)
    pipeline_stages = construire_pipeline_px8(donnees)
    if mode_vide:
        pipeline_stages = [
            stage if stage.get("key") in {"flux_x", "filtre_1", "filtre_2"} else {**stage, "key": None, "disabled": True}
            for stage in pipeline_stages
        ]
    tabs = [{"key": step["key"], "label": step["label"]} for step in steps]
    vues_valides = {step["key"] for step in steps} | {stage["key"] for stage in pipeline_stages if stage.get("key")} | {"flux_x", "filtre_1", "filtre_2", "declencheur_1", "declencheur_2", "script_1", "filtre_3", "proposition_reformulation", "proposition_reponse", "proposition_validation", "aucun"}
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


def afficher_vue_vide() -> None:
    render_react_header(
        "Cuisine agentique - Datathon PX8",
        "De la crise brute aux agents : acteurs, propagation, viralité, coordination, narratifs, sémantique, proposition.",
    )
    vue_active = choisir_vue_timeline({}, mode_vide=True)
    if vue_active == "flux_x":
        afficher_vue_flux_x()
    elif vue_active == "filtre_1":
        afficher_vue_filtre_1()
    elif vue_active == "filtre_2":
        afficher_vue_filtre_2()


def afficher_vue_cuisine(donnees: dict) -> None:
    vue_active = choisir_vue_timeline(donnees)

    if vue_active == "flux_x":
        afficher_vue_flux_x()
    elif vue_active == "filtre_1":
        afficher_vue_filtre_1()
    elif vue_active == "filtre_2":
        afficher_vue_filtre_2()
    elif vue_active == "declencheur_1":
        afficher_brique_declencheur_volume(donnees)
    elif vue_active == "declencheur_2":
        afficher_brique_declencheur_significativite(donnees)
    elif vue_active == "acteurs":
        afficher_brique_acteurs(donnees)
    elif vue_active == "propagation":
        afficher_brique_propagation(donnees)
    elif vue_active == "viralite":
        afficher_brique_viralite(donnees)
    elif vue_active == "coordination":
        afficher_brique_coordination(donnees)
    elif vue_active == "narratifs":
        afficher_brique_narratifs(donnees)
    elif vue_active == "script_1":
        afficher_brique_script_significativite(donnees)
    elif vue_active == "filtre_3":
        afficher_brique_filtre_risque(donnees)
    elif vue_active == "semantique":
        afficher_brique_semantique(donnees)
    elif vue_active == "proposition_reformulation":
        afficher_brique_proposition_reformulation(donnees)
    elif vue_active == "proposition_reponse":
        afficher_brique_proposition_reponse(donnees)
    elif vue_active == "proposition_validation":
        afficher_brique_proposition_validation(donnees)
    elif vue_active == "proposition":
        afficher_brique_proposition(donnees)


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


def afficher_brique_acteurs(donnees: dict) -> None:
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame):
        st.info("Dataset non chargé.")
        return

    top_auteurs = dataset["Author"].value_counts().head(10).reset_index()
    top_auteurs.columns = ["Auteur", "Messages"]
    originaux = int(dataset.get("_is_original", pd.Series(dtype=bool)).sum()) if "_is_original" in dataset else 0
    retweets = int((dataset.get("Engagement Type") == "RETWEET").sum()) if "Engagement Type" in dataset else 0

    afficher_contrat_agent(
        "Brique acteurs - qui parle et qui relaie ?",
        "Acteurs",
        [
            "Dataset préparé par ChargementDataset.",
            "Colonnes attendues : Author, X Followers, X Verified, Engagement Type, X Repost of.",
            f"Volume reçu : {len(dataset):,} lignes et {len(dataset.columns):,} colonnes.",
        ],
        [
            "Extraction des auteurs originaux depuis les URL de repost.",
            "Séparation messages originaux / retweets / réponses.",
            "Comptage des auteurs actifs et des sources amplifiées.",
            "Préparation du terrain pour les agents viralité et coordination.",
        ],
        {
            "Messages": f"{len(dataset):,}",
            "Auteurs": f"{dataset['Author'].nunique():,}" if "Author" in dataset else "n/a",
            "Originaux": f"{originaux:,}",
            "Retweets": f"{retweets:,}",
        },
        [
            "DataFrame enrichi avec _source, _status_id, _is_original.",
            "Liste des auteurs et sources mobilisables par viralité / coordination.",
        ],
    )
    col_gauche, col_droite = st.columns([1.1, 0.9])
    with col_gauche:
        fig = graphique_top_auteurs(donnees)
        if fig is not None:
            expliquer_graphe(
                "Quels comptes produisent ou relaient le plus de messages ?",
                "Plus la barre est longue, plus le compte pèse dans le bruit total. Cela identifie les acteurs à surveiller avant de parler de narratif.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_types_engagement(donnees)
        if fig is not None:
            expliquer_graphe(
                "Est-ce une crise de prise de parole ou surtout d'amplification ?",
                "Une forte part de retweets signifie que la dynamique vient surtout du relais collectif, pas seulement de nouveaux messages originaux.",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Table de contrôle : top auteurs**")
    st.dataframe(top_auteurs, use_container_width=True, hide_index=True)


def afficher_brique_declencheur_volume(donnees: dict) -> None:
    dataset = donnees.get("dataset")
    pic = donnees.get("proposition", {}).get("chiffres_cles", {}).get("pic", {})
    alerte = etat_alerte_trigger_volume(donnees)
    seuil = alerte["seuil"]
    messages_au_dessus = alerte["messages_au_dessus"]

    afficher_contrat_agent(
        "Trigger 1 - volume et seuil d'alerte",
        "Déclencheur / propagation",
        [
            "Messages datés avec Date et Impressions.",
            "Seuil d'alerte attendu : SEUIL_IMPRESSION, défaut 5000.",
            "Dataset filtré et nettoyé par les deux premiers filtres.",
        ],
        [
            "Conversion des impressions en valeurs numériques.",
            "Recherche des messages au-dessus du seuil d'alerte.",
            "Agrégation quotidienne pour repérer le pic de volume.",
            "Décision : poursuivre la lecture propagation si le signal dépasse le bruit.",
        ],
        {
            "Messages": f"{len(dataset):,}" if isinstance(dataset, pd.DataFrame) else "n/a",
            "Seuil": f"{seuil:,}",
            "Au-dessus": f"{messages_au_dessus:,}",
            "Pic": f"{pic.get('messages', 0):,}",
        },
        [
            "Signal déclencheur pour l'écran Propagation.",
            "Pic temporel à relier aux événements publics.",
            "Base de comparaison pour la significativité.",
        ],
    )
    if alerte["alerte"]:
        st.markdown('<div style="text-align:center"><span class="px8-red-alert">Red Alert</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center"><span class="px8-no-alert">Aucune alerte</span></div>', unsafe_allow_html=True)
    fig = graphique_volume_journalier(donnees)
    if fig is not None:
        expliquer_graphe(
            "Quand le sujet franchit-il un seuil visible ?",
            "Le trigger volume sert à repérer le moment où la crise cesse d'être diffuse et devient observable dans le flux.",
        )
        st.plotly_chart(fig, use_container_width=True)


def afficher_brique_declencheur_significativite(donnees: dict) -> None:
    dataset = donnees.get("dataset")
    concentration = donnees.get("concentration", {})
    auteurs_uniques = "n/a"
    comptes_certifies = "n/a"
    if isinstance(dataset, pd.DataFrame):
        if "Author" in dataset.columns:
            auteurs_uniques = f"{dataset['Author'].nunique():,}"
        if "X Verified" in dataset.columns:
            comptes_certifies = f"{pd.Series(dataset['X Verified']).fillna(False).astype(bool).sum():,}"

    afficher_contrat_agent(
        "Trigger 2 - significativité du signal",
        "Déclencheur / propagation",
        [
            "Messages nettoyés avec Author, X Verified, X Followers et Engagement Type.",
            "Retweets enrichis avec la source amplifiée.",
            "Sorties du trigger volume pour contextualiser le pic.",
        ],
        [
            "Comptage des comptes uniques mobilisés.",
            "Lecture de la présence de comptes certifiés.",
            "Calcul de concentration : Gini contenu, Gini relais, part du top 20.",
            "Qualification du signal : bruit isolé ou propagation structurée.",
        ],
        {
            "Auteurs uniques": auteurs_uniques,
            "Certifiés": comptes_certifies,
            "Gini contenu": concentration.get("gini_contenu", "n/a"),
            "Top 20 RT": f"{concentration.get('top20_share_pct', 'n/a')}%",
        },
        [
            "Niveau de significativité transmis à Propagation.",
            "Liste des sources amplifiées.",
            "Base d'analyse pour coordination et narratifs.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        graphique_gini = donnees.get("graphique_gini")
        if graphique_gini is not None:
            expliquer_graphe(
                "Le relais est-il concentré entre quelques sources ?",
                "Un Gini élevé indique qu'une petite partie des contenus ou relais structure fortement la circulation.",
            )
            st.plotly_chart(graphique_gini, use_container_width=True)
    with col_droite:
        graphique_amplificateurs = donnees.get("graphique_amplificateurs")
        if graphique_amplificateurs is not None:
            expliquer_graphe(
                "Qui porte la propagation visible ?",
                "Les premiers amplificateurs montrent les sources qui donnent de la portée au sujet.",
            )
            st.plotly_chart(graphique_amplificateurs, use_container_width=True)


def afficher_brique_propagation(donnees: dict) -> None:
    concentration = donnees.get("concentration", {})
    pic = donnees.get("proposition", {}).get("chiffres_cles", {}).get("pic", {})
    afficher_contrat_agent(
        "Brique propagation - quand la crise bascule ?",
        "Propagation",
        [
            "Messages datés avec Date, Impressions, Engagement Type.",
            "Seuil d'impressions configurable : SEUIL_IMPRESSION, défaut 5000.",
            "Retweets enrichis avec source amplifiée.",
        ],
        [
            "Détection d'au moins un message au-dessus du seuil d'impressions.",
            "Calcul de concentration des sources amplifiées.",
            "Indice de Gini contenu et relais.",
            "Part des 20 premières sources dans les retweets.",
        ],
        {
            "Pic": f"{pic.get('messages', 0):,}",
            "Date pic": pic.get("date", "n/a"),
            "Gini contenu": concentration.get("gini_contenu", "n/a"),
            "Top 20 RT": f"{concentration.get('top20_share_pct', 'n/a')}%",
        },
        [
            "Signal de poursuite ou arrêt de la pipeline.",
            "Amplificateurs principaux.",
            "Graphiques Gini et amplificateurs.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_volume_journalier(donnees)
        if fig is not None:
            expliquer_graphe(
                "À quel moment la conversation devient-elle une crise visible ?",
                "Les pics indiquent les jours où le sujet sort du bruit normal. C'est le moment à relier aux événements et aux relais majeurs.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_sentiment_journalier(donnees)
        if fig is not None:
            expliquer_graphe(
                "Le pic est-il seulement volumétrique ou aussi émotionnel ?",
                "Si la zone négative monte avec le volume, la crise n'est pas seulement bruyante : elle devient réputationnelle.",
            )
            st.plotly_chart(fig, use_container_width=True)
    amplificateurs = donnees.get("amplificateurs")
    if isinstance(amplificateurs, pd.DataFrame):
        st.markdown("**Sources amplifiées : qui sert de point d'appui au relais ?**")
        st.dataframe(amplificateurs.head(10), use_container_width=True, hide_index=True)


def afficher_brique_viralite(donnees: dict) -> None:
    dataset = donnees.get("dataset")
    classes = dataset["Classe_viralite"].value_counts().to_dict() if isinstance(dataset, pd.DataFrame) and "Classe_viralite" in dataset else {}
    afficher_contrat_agent(
        "Agent 1 - ce message peut-il être viral ?",
        "Propagation / priorisation",
        [
            "DataFrame enrichi par les acteurs et la propagation.",
            "Colonnes attendues : X Followers, X Verified, X Posts, Hashtags, Full Text.",
            "Chaque ligne est transformée en features numériques.",
        ],
        [
            "Modèle utilisé : sklearn Pipeline sauvegardé en joblib.",
            "Features : followers, compte vérifié, volume de posts, nombre de hashtags, longueur du texte.",
            "Sortie probabiliste si predict_proba existe.",
            "Classification par seuils : Non Viral, Moyennement Viral, Viral.",
        ],
        {
            "Viral": classes.get("Viral", 0),
            "Moyen": classes.get("Moyennement Viral", 0),
            "Non viral": classes.get("Non Viral", 0),
        },
        [
            "Colonnes ajoutées : Viralite et Classe_viralite.",
            "Décision de continuer si au moins un contenu est viral.",
            "Signal de priorité pour la suite narrative.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_viralite_distribution(donnees)
        if fig is not None:
            expliquer_graphe(
                "Combien de contenus méritent une attention prioritaire ?",
                "L'agent ne dit pas que tout est grave : il trie les messages selon leur potentiel d'exposition.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_viralite_reach(donnees)
        if fig is not None:
            expliquer_graphe(
                "La viralité vient-elle de gros comptes ou de contenus très relayés ?",
                "Un point haut avec peu d'abonnés signale une amplification collective ; un point haut avec beaucoup d'abonnés signale une audience structurelle.",
            )
            st.plotly_chart(fig, use_container_width=True)


def afficher_brique_coordination(donnees: dict) -> None:
    communaute = donnees.get("communaute", {})
    communautes = donnees.get("communautes", [])
    afficher_contrat_agent(
        "Brique coordination - qui amplifie ensemble ?",
        "Coordination / polarisation",
        [
            "Retweets avec Author et _source.",
            "Sources relayées au moins 10 fois.",
            "Graphe biparti retweeteur <-> source amplifiée.",
        ],
        [
            "Construction d'un graphe NetworkX pondéré.",
            "Détection de communautés par algorithme de Louvain.",
            "Calcul de modularité.",
            "Filtrage des communautés sous le seuil de messages.",
        ],
        {
            "Communautés": len(communautes),
            "Modularité": communaute.get("modularite", "n/a") if isinstance(communaute, dict) else "n/a",
            "Auteurs": communaute.get("nombre_auteurs_communautarises", "n/a") if isinstance(communaute, dict) else "n/a",
        },
        [
            "Liste de communautés caractérisées.",
            "Sources pivots par communauté.",
            "Dataset communautaire envoyé à l'analyse de langage.",
        ],
    )
    if communautes:
        col_gauche, col_droite = st.columns(2)
        with col_gauche:
            fig = graphique_communautes_risque(donnees)
            if fig is not None:
                expliquer_graphe(
                    "Quelles communautés sont grosses, négatives et structurées ?",
                    "La taille représente le nombre de retweeteurs. Une communauté haut placée est plus négative ; à droite, elle pèse plus en volume.",
                )
                st.plotly_chart(fig, use_container_width=True)
        with col_droite:
            fig = graphique_sources_pivots(donnees)
            if fig is not None:
                expliquer_graphe(
                    "Quels comptes ou sources servent de points de ralliement ?",
                    "Ces sources pivots ne sont pas forcément les plus bavardes : ce sont celles que les communautés amplifient ensemble.",
                )
                st.plotly_chart(fig, use_container_width=True)

        table_communautes = dataframe_communautes(donnees)
        table_communautes = table_communautes.drop(columns=["sources_lisibles"], errors="ignore")
        st.markdown("**Table de contrôle : communautés détectées par Louvain**")
        st.dataframe(dataframe_tableau_lisible(table_communautes), use_container_width=True, hide_index=True)


def afficher_brique_narratifs(donnees: dict) -> None:
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
    afficher_contrat_agent(
        "Agent 2 - NLP narratif",
        "Narratifs",
        [
            "Corpus texte issu de message_normalizer ou Full Text.",
            "Colonne Sentiment pour évaluer la négativité par récit.",
            "Doublons conservés pour le volume, textes uniques pour l'analyse.",
        ],
        [
            "Nettoyage léger : URLs et espaces.",
            "Déduplication des textes.",
            "Vectorisation TF-IDF, ngrammes 1 à 2, stop words français.",
            "Clustering KMeans pour extraire les récits.",
            "Score de risque = volume relatif + part négative.",
        ],
        {
            "Récits": len(recits),
            "Corpus": narratif.get("corpus", {}).get("messages_total", "n/a") if isinstance(narratif, dict) else "n/a",
            "Analysés": narratif.get("corpus", {}).get("messages_analyses", "n/a") if isinstance(narratif, dict) else "n/a",
        },
        [
            "Liste de récits avec mots-clés, exemple, volume, négativité, score risque.",
            "RAG simple : exemples représentatifs par récit.",
            "Récit prioritaire transmis à Agent 3.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_recits(donnees)
        if fig is not None:
            expliquer_graphe(
                "Quels récits structurent vraiment la conversation ?",
                "Le volume montre ce qui est visible. La couleur rappelle qu'un récit visible n'est pas toujours le plus agressif.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_recits_risque(donnees)
        if fig is not None:
            expliquer_graphe(
                "Quel récit faut-il traiter en priorité ?",
                "La priorité vient du croisement volume + négativité. Un petit récit très négatif peut être plus sensible qu'un gros récit neutre.",
            )
            st.plotly_chart(fig, use_container_width=True)

    fig = graphique_corpus_doublons(donnees)
    if fig is not None:
        expliquer_graphe(
            "Pourquoi l'agent NLP ignore-t-il une partie des messages ?",
            "Les doublons comptent pour mesurer le volume, mais ils sont retirés pour mieux comprendre les thèmes sans répéter mille fois le même texte.",
        )
        st.plotly_chart(fig, use_container_width=True)


def afficher_brique_script_significativite(donnees: dict) -> None:
    dataset = donnees.get("dataset")
    narratif = donnees.get("narratif", {})
    tonalite = narratif.get("tonalite", {}) if isinstance(narratif, dict) else {}
    repartition = tonalite.get("repartition", {}) if isinstance(tonalite, dict) else {}
    certifies = "n/a"
    followers_median = "n/a"
    if isinstance(dataset, pd.DataFrame):
        if "X Verified" in dataset.columns:
            certifies = f"{pd.Series(dataset['X Verified']).fillna(False).astype(bool).sum():,}"
        if "X Followers" in dataset.columns:
            followers = pd.to_numeric(dataset["X Followers"], errors="coerce").dropna()
            if not followers.empty:
                followers_median = f"{int(followers.median()):,}"

    afficher_contrat_agent(
        "Script 1 - significativité sémantique",
        "Sémantique / significativité",
        [
            "Corpus enrichi avec texte normalisé, sentiment, comptes et métadonnées sociales.",
            "Colonnes attendues : Sentiment, X Verified, X Followers, Author.",
            "Sortie NLP de l'agent narratif pour relier thèmes et tonalité.",
        ],
        [
            "Comptage des tonalités positives, neutres et négatives.",
            "Lecture du poids des comptes certifiés et de l'audience médiane.",
            "Croisement entre tonalité, visibilité sociale et récits structurants.",
            "Production d'un signal de significativité avant scoring de risque.",
        ],
        {
            "Négatifs": f"{repartition.get('negative', 0):,}",
            "Neutres": f"{repartition.get('neutral', 0):,}",
            "Certifiés": certifies,
            "Followers méd.": followers_median,
        },
        [
            "Signal sémantique consolidé.",
            "Tonalité exploitable par le filtre de risque.",
            "Indicateurs lisibles pour la proposition client.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_sentiment_global(donnees)
        if fig is not None:
            expliquer_graphe(
                "La matière analysée est-elle plutôt neutre ou hostile ?",
                "Ce script transforme la masse de messages en signal sémantique lisible.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_sentiment_journalier(donnees)
        if fig is not None:
            expliquer_graphe(
                "La tonalité change-t-elle au moment des pics ?",
                "La significativité augmente quand le volume et la négativité montent ensemble.",
            )
            st.plotly_chart(fig, use_container_width=True)


def afficher_brique_filtre_risque(donnees: dict) -> None:
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
    recit_prioritaire = max(recits, key=lambda recit: recit.get("score_risque", 0), default={})

    afficher_contrat_agent(
        "Filtre 3 - risque sémantique",
        "Sémantique / risque",
        [
            "Récits issus de l'agent NLP.",
            "Pour chaque récit : volume, part négative, score de risque et exemples.",
            "Signal de significativité produit par Script 1.",
        ],
        [
            "Croisement volume relatif + agressivité / négativité.",
            "Priorisation des récits qui combinent visibilité et danger réputationnel.",
            "Filtrage des signaux faibles trop peu structurés.",
            "Sélection du récit à traiter dans la proposition finale.",
        ],
        {
            "Récits": len(recits),
            "Prioritaire": recit_prioritaire.get("nom", "n/a"),
            "Score": recit_prioritaire.get("score_risque", "n/a"),
            "% nég.": f"{recit_prioritaire.get('pct_negative', 'n/a')}%",
        },
        [
            "Récit prioritaire qualifié.",
            "Niveau de risque transmis à Sémantique et Proposition.",
            "Arguments pour décider quoi répondre, et quoi éviter.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_recits_risque(donnees)
        if fig is not None:
            expliquer_graphe(
                "Quel récit est le plus risqué, pas seulement le plus visible ?",
                "Le filtre évite de répondre au bruit majoritaire si un récit plus petit est beaucoup plus agressif.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_recits(donnees)
        if fig is not None:
            expliquer_graphe(
                "Comment le risque se répartit-il entre les récits ?",
                "Cette lecture prépare la décision éditoriale : prioriser, temporiser ou ignorer.",
            )
            st.plotly_chart(fig, use_container_width=True)


def afficher_brique_semantique(donnees: dict) -> None:
    tonalite = donnees.get("narratif", {}).get("tonalite", {})
    repartition = tonalite.get("repartition", {}) if isinstance(tonalite, dict) else {}
    afficher_contrat_agent(
        "Brique sémantique - quelle tonalité domine ?",
        "Sémantique / sentiment",
        [
            "Colonne Sentiment déjà présente dans le corpus.",
            "Messages groupés par récit et communauté.",
            "Texte normalisé pour relier tonalité et narratif.",
        ],
        [
            "Répartition positive / neutre / négative.",
            "Calcul de part négative globale.",
            "Calcul de part négative par récit et par communauté.",
            "Utilisation de la négativité comme facteur de risque.",
        ],
        {
            "Négatif": f"{tonalite.get('part_negative', 'n/a')}%",
            "Neutre": f"{tonalite.get('part_neutral', 'n/a')}%",
            "Positif": f"{tonalite.get('part_positive', 'n/a')}%",
        },
        [
            "Tonalité globale de crise.",
            "Récits plus dangereux que leur seul volume.",
            "Arguments de priorisation pour la proposition finale.",
        ],
    )
    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        fig = graphique_sentiment_global(donnees)
        if fig is not None:
            expliquer_graphe(
                "La conversation est-elle majoritairement hostile ?",
                "Le sentiment global donne la température de la crise : neutre, défensive, ou franchement négative.",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col_droite:
        fig = graphique_sentiment_journalier(donnees)
        if fig is not None:
            expliquer_graphe(
                "La négativité se concentre-t-elle sur certains jours ?",
                "Une montée courte et intense appelle une réponse rapide ; une négativité durable appelle plutôt une stratégie de clarification dans le temps.",
            )
            st.plotly_chart(fig, use_container_width=True)


def afficher_brique_proposition_reformulation(donnees: dict) -> None:
    proposition = donnees.get("proposition", {})
    afficher_contrat_agent(
        "Agent 3 - reformulation stratégique",
        "Proposition / reformulation",
        [
            "Récit prioritaire issu du filtre de risque.",
            "Tonalité, concentration, amplificateurs et niveau de risque.",
            "Contraintes de rédaction : neutralité, prudence, validation humaine.",
        ],
        [
            "Transformation des signaux techniques en diagnostic éditorial.",
            "Choix d'une stratégie de réponse adaptée au risque.",
            "Identification des angles à traiter et des formulations à éviter.",
            "Préparation du brief pour la réponse générée.",
        ],
        {
            "Stratégie": proposition.get("strategie", "n/a"),
            "Risque": proposition.get("niveau_risque", "n/a"),
            "Priorité": proposition.get("priorite", "n/a"),
        },
        [
            "Diagnostic reformulé pour décideur.",
            "Messages clés à intégrer dans la réponse.",
            "Contraintes transmises au module de réponse.",
        ],
    )
    st.markdown("**Synthèse exécutive préparée**")
    st.write(proposition.get("synthese_executive", "Synthèse non disponible."))


def afficher_brique_proposition_reponse(donnees: dict) -> None:
    proposition = donnees.get("proposition", {})
    afficher_contrat_agent(
        "Proposition - réponse générée",
        "Proposition / réponse",
        [
            "Brief reformulé par Agent 3.",
            "Messages clés, points à valider et messages à éviter.",
            "Placeholders obligatoires pour empêcher une publication automatique.",
        ],
        [
            "Rédaction d'un brouillon de réponse.",
            "Conservation d'un ton factuel et vérifiable.",
            "Ajout volontaire de garde-fous et de zones à compléter.",
            "Sortie non publiable sans contrôle humain.",
        ],
        {
            "Brouillon": "Disponible" if proposition.get("reponse_brouillon") else "n/a",
            "Messages clés": len(proposition.get("messages_cles", [])),
            "À valider": len(proposition.get("points_a_valider", [])),
        },
        [
            "Brouillon de réponse.",
            "Liste des messages clés.",
            "Points à vérifier avant validation.",
        ],
    )
    st.text_area("Brouillon de réponse", value=proposition.get("reponse_brouillon", ""), height=220)


def afficher_brique_proposition_validation(donnees: dict) -> None:
    proposition = donnees.get("proposition", {})
    afficher_contrat_agent(
        "Validation - décision humaine",
        "Décision / validation",
        [
            "Brouillon de réponse généré.",
            "Diagnostic, niveau de risque et délai recommandé.",
            "Points à valider et messages à éviter.",
        ],
        [
            "Contrôle éditorial par un responsable humain.",
            "Décision : publier, modifier ou ignorer.",
            "Vérification des faits, du ton et des placeholders.",
            "Blocage de toute publication automatique.",
        ],
        {
            "Priorité": proposition.get("priorite", "n/a"),
            "Délai": proposition.get("delai_recommande", "n/a"),
            "Validation": "Obligatoire",
        },
        [
            "Décision finale documentée.",
            "Réponse modifiée ou validée.",
            "Publication uniquement après accord humain.",
        ],
    )
    col_eviter, col_valider = st.columns(2)
    with col_eviter:
        st.markdown("**À éviter**")
        for item in proposition.get("messages_a_eviter", []):
            st.write(f"- {item}")
    with col_valider:
        st.markdown("**À valider**")
        for item in proposition.get("points_a_valider", []):
            st.write(f"- {item}")


def afficher_brique_proposition(donnees: dict) -> None:
    proposition = donnees.get("proposition", {})
    afficher_contrat_agent(
        "Agent 3 - proposition de réponse",
        "Réponse / orchestration",
        [
            "Récit prioritaire, tonalité, concentration, amplificateurs.",
            "Sorties validées des agents précédents.",
            "Contraintes : neutralité, pas d'invention, validation humaine.",
        ],
        [
            "Synthèse exécutive de la crise.",
            "Choix d'une stratégie : clarification factuelle.",
            "Identification des messages clés, risques, éléments à éviter.",
            "Rédaction d'un brouillon avec placeholders obligatoires.",
        ],
        {
            "Priorité": proposition.get("priorite", "n/a"),
            "Risque": proposition.get("niveau_risque", "n/a"),
            "Stratégie": proposition.get("strategie", "n/a"),
        },
        [
            "Vue client final.",
            "Brouillon non publiable sans validation.",
            "Décision humaine : publier, modifier ou ignorer.",
        ],
    )
    st.text_area("Brouillon Agent 3", value=proposition.get("reponse_brouillon", ""), height=180)


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


def afficher_vue_flux_x() -> None:
    st.markdown('<div class="px8-import-title">Collecte Flux X</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            """
            <div class="px8-import-bar">
                <span style="font-size: 1.2rem;">⌄</span>
                <span>Source brute et récupération du corpus</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.markdown(
                """
                <p class="px8-import-help">
                    Choisis la porte d'entrée du corpus : fichier Excel déjà constitué, chemin local du projet,
                    ou future collecte X via API / scraping. La sortie attendue est le dataset brut qui alimente
                    les filtres puis les agents.
                </p>
                """,
                unsafe_allow_html=True,
            )

            source = st.radio(
                "Source de données",
                ["Dataset Excel", "Chemin projet", "API / Scraping X"],
                horizontal=True,
                label_visibility="collapsed",
                key="flux_x_source_import",
            )

            if source == "Dataset Excel":
                st.markdown('<div class="px8-import-tabs-note">Dataset Excel</div>', unsafe_allow_html=True)
                fichier = st.file_uploader("Fichier .xlsx", type=["xlsx"], key="flux_x_fichier_excel")
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

            elif source == "Chemin projet":
                st.markdown('<div class="px8-import-tabs-note">Chemin projet</div>', unsafe_allow_html=True)
                chemin_defaut = st.text_input(
                    "Chemin du dataset",
                    value=st.session_state.get("dernier_chemin_pipeline", "data_source/data.xlsx"),
                    key="flux_x_chemin_local",
                )
                st.markdown(
                    '<p class="px8-import-dependency">Source locale du projet, par exemple : <code>data_source/data.xlsx</code>.</p>',
                    unsafe_allow_html=True,
                )
                if st.button("Lancer la collecte depuis ce chemin", type="primary"):
                    lancer_pipeline_depuis_chemin(chemin_defaut)
                    st.success(f"Pipeline exécutée depuis {chemin_defaut}.")

            else:
                st.markdown('<div class="px8-import-tabs-note">Collecte X</div>', unsafe_allow_html=True)
                col_mode, col_volume = st.columns([1, 1])
                with col_mode:
                    mode_collecte = st.selectbox(
                        "Mode de collecte",
                        ["Search API", "Stream API", "Scraping contrôlé"],
                        key="flux_x_mode_collecte",
                    )
                with col_volume:
                    volume_max = st.number_input(
                        "Volume maximal",
                        min_value=100,
                        max_value=500000,
                        value=50000,
                        step=1000,
                        key="flux_x_volume_max",
                    )
                st.markdown(
                    '<p class="px8-import-dependency">À brancher : <code>credentials</code>, pagination, limites d’usage, normalisation et stockage brut.</p>',
                    unsafe_allow_html=True,
                )
                st.json(
                    {
                        "mode": mode_collecte,
                        "volume_max": int(volume_max),
                        "sortie": "tweets bruts normalisés avant filtres",
                    }
                )

    afficher_source_active()


def afficher_vue_filtre_1() -> None:
    st.title("Filtre 1 - Requête")
    st.caption("Définir le périmètre de collecte : mots-clés, comptes, hashtags et origine.")

    col_requete, col_ciblage = st.columns(2)
    with col_requete:
        with bloc_ecran("Requête & mots-clés"):
            requete = st.text_input("Requête X", value='("CNC" OR "CNC Talent" OR "Ultia") lang:fr', key="filtre_1_requete")
            hashtags = st.text_input("Hashtags", value="#CNC,#CNCTalent,#Ultia", key="filtre_1_hashtags")
    with col_ciblage:
        with bloc_ecran("Ciblage"):
            comptes = st.text_area("Comptes / origines", value="ultia\noffinvestigatio\ncharlesvillaa", height=120, key="filtre_1_comptes")
            langue = st.selectbox("Langue", ["fr", "en", "all"], key="filtre_1_langue")

    config = {
        "requete": requete,
        "hashtags": [tag.strip() for tag in hashtags.split(",") if tag.strip()],
        "comptes": [ligne.strip() for ligne in comptes.splitlines() if ligne.strip()],
        "langue": langue,
        "sortie": "tweets bruts filtrés par périmètre de crise",
    }
    if st.button("Valider le filtre 1", type="primary"):
        st.session_state["filtre_1_config"] = config
        st.success("Filtre 1 enregistré.")
    with bloc_ecran("Contrat filtre 1"):
        st.json(st.session_state.get("filtre_1_config", config))


def afficher_vue_filtre_2() -> None:
    st.title("Filtre 2 - Nettoyage & enrichissement")
    st.caption("Préparer les données avant agents : langue, doublons, retweets, métadonnées.")

    col_nettoyage, col_sortie = st.columns(2)
    with col_nettoyage:
        with bloc_ecran("Nettoyage"):
            dedoublonner = st.checkbox("Supprimer les doublons textuels", value=True, key="filtre_2_dedoublonner")
            inclure_retweets = st.checkbox("Conserver les retweets / reposts", value=True, key="filtre_2_retweets")
            enrichir_sources = st.checkbox("Extraire _source et _status_id", value=True, key="filtre_2_sources")
            normaliser_texte = st.checkbox("Normaliser le texte pour NLP", value=True, key="filtre_2_normaliser")
    with col_sortie:
        with bloc_ecran("Colonnes attendues"):
            st.write("- Date, Author, Full Text, message_normalizer")
            st.write("- Sentiment, Impressions, Reach, Engagement Type")
            st.write("- X Repost of, _source, _status_id, _is_original")

    config = {
        "dedoublonner": bool(dedoublonner),
        "inclure_retweets": bool(inclure_retweets),
        "enrichir_sources": bool(enrichir_sources),
        "normaliser_texte": bool(normaliser_texte),
        "sortie": "DataFrame compatible avec ChargementDataset et agents PX8",
    }
    if st.button("Valider le filtre 2", type="primary"):
        st.session_state["filtre_2_config"] = config
        st.success("Filtre 2 enregistré.")
    with bloc_ecran("Contrat filtre 2"):
        st.json(st.session_state.get("filtre_2_config", config))


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


def main() -> None:
    st.set_page_config(page_title="Pipeline Agent X", layout="wide")
    appliquer_style_typographique()

    if "donnees_pipeline" not in st.session_state:
        afficher_vue_vide()
        st.stop()

    mode_vue = afficher_header_principal_avec_toggle()
    donnees = st.session_state["donnees_pipeline"]

    if mode_vue == "Client":
        afficher_vue_client(donnees)
    else:
        afficher_vue_cuisine(donnees)


if __name__ == "__main__":
    main()
