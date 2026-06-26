from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st

from pipeline.ui.view_utils import *


def injecter_style_communautes() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #142033;
            --muted: #637083;
            --line: #dbe4ef;
        }
        .kpi-card {
            border-radius: 8px;
            padding: 20px 20px 18px;
            color: white;
            min-height: 130px;
            box-shadow: 0 16px 34px rgba(16, 24, 40, 0.16);
            border: 1px solid rgba(255,255,255,0.26);
        }
        .kpi-title {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            opacity: 0.86;
            margin-bottom: 8px;
        }
        .kpi-value {
            font-size: 2.08rem;
            font-weight: 800;
            line-height: 1.05;
            margin-bottom: 8px;
        }
        .kpi-detail {
            font-size: 0.92rem;
            opacity: 0.92;
            line-height: 1.25;
        }
        .message-card {
            border-radius: 8px;
            padding: 20px;
            background: rgba(255,255,255,0.96);
            border: 1px solid var(--line);
            box-shadow: 0 14px 32px rgba(16, 24, 40, 0.10);
            margin: 12px 0;
        }
        .message-meta {
            color: var(--muted);
            font-size: 0.92rem;
            margin-bottom: 10px;
        }
        .message-text {
            color: var(--ink);
            font-size: 1rem;
            line-height: 1.42;
        }
        .section-lead {
            color: var(--muted);
            font-size: 1.03rem;
            margin-top: -0.25rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def formater_nombre(valeur) -> str:
    if valeur is None:
        return "n/a"
    try:
        if pd.isna(valeur):
            return "n/a"
        return f"{int(float(valeur)):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(valeur)


def carte_indicateur(titre: str, valeur, detail: str = "", couleur: str = "#2563eb") -> None:
    st.markdown(
        f"""
        <div class="kpi-card" style="background:{couleur};">
            <div class="kpi-title">{escape(titre)}</div>
            <div class="kpi-value">{escape(formater_nombre(valeur))}</div>
            <div class="kpi-detail">{escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def carte_message(titre: str, meta: str, texte: str, couleur_bordure: str = "#2563eb") -> None:
    st.markdown(
        f"""
        <div class="message-card" style="border-left: 6px solid {couleur_bordure};">
            <div class="kpi-title" style="color:{couleur_bordure};">{escape(titre)}</div>
            <div class="message-meta">{escape(meta)}</div>
            <div class="message-text">{escape(str(texte))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sources_pivots_liste(groupe: dict) -> list[str]:
    sources = []
    for item in groupe.get("sources_pivots", []) or []:
        if isinstance(item, (list, tuple)) and item:
            sources.append(str(item[0]))
        elif item:
            sources.append(str(item))
    return sources


def dataset_groupe(dataset: pd.DataFrame, groupe: dict) -> pd.DataFrame:
    if not isinstance(dataset, pd.DataFrame) or dataset.empty:
        return pd.DataFrame()

    sources = sources_pivots_liste(groupe)
    if sources and "_source" in dataset.columns:
        groupe_dataset = dataset[dataset["_source"].isin(sources)].copy()
        if not groupe_dataset.empty:
            return groupe_dataset

    return pd.DataFrame()


def profil_groupe(dataset: pd.DataFrame, groupe: dict) -> dict:
    groupe_dataset = dataset_groupe(dataset, groupe)
    profil = dict(groupe)

    profil.setdefault("nombre_auteurs", 0)
    profil.setdefault("followers_total", 0)
    profil.setdefault("comptes_verifies", 0)
    profil.setdefault("compte_influent", "")

    if groupe_dataset.empty:
        return profil

    if "Author" in groupe_dataset.columns:
        profil["nombre_auteurs"] = int(groupe_dataset["Author"].nunique())

    if {"Author", "X Followers"}.issubset(groupe_dataset.columns):
        followers = groupe_dataset[["Author", "X Followers"]].copy()
        followers["X Followers"] = pd.to_numeric(followers["X Followers"], errors="coerce").fillna(0)
        followers_par_auteur = followers.groupby("Author")["X Followers"].max().sort_values(ascending=False)
        profil["followers_total"] = int(followers_par_auteur.sum())
        if not followers_par_auteur.empty:
            profil["compte_influent"] = str(followers_par_auteur.index[0])

    if {"Author", "X Verified"}.issubset(groupe_dataset.columns):
        verifies = groupe_dataset[["Author", "X Verified"]].drop_duplicates("Author")
        profil["comptes_verifies"] = int(verifies["X Verified"].fillna(False).astype(bool).sum())

    return profil


def construire_activite_temporelle(dataset: pd.DataFrame, groupes: list[dict]) -> list[dict]:
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Date" not in dataset.columns:
        return []

    lignes = []
    for groupe in groupes:
        groupe_dataset = dataset_groupe(dataset, groupe)
        if groupe_dataset.empty:
            continue

        dates = pd.to_datetime(groupe_dataset["Date"], errors="coerce").dropna()
        if dates.empty:
            continue

        activite = dates.dt.floor("D").value_counts().sort_index()
        for date, messages in activite.items():
            lignes.append(
                {
                    "Date": date,
                    "messages": int(messages),
                    "communaute": groupe.get("id_original", groupe.get("id")),
                    "groupe": groupe.get("rang_activite"),
                    "nom_groupe": groupe.get("nom_groupe"),
                }
            )
    return lignes


def assembler_communautes(donnees: dict) -> dict:
    communaute = donnees.get("communaute", {}) if isinstance(donnees.get("communaute"), dict) else {}
    dataset = donnees.get("dataset")
    groupes_source = communaute.get("communautes") or donnees.get("communautes", [])
    groupes_tries = sorted(groupes_source, key=lambda item: item.get("nombre_messages", 0), reverse=True)

    groupes = []
    for rang, groupe in enumerate(groupes_tries, start=1):
        profil = profil_groupe(dataset, groupe)
        profil["id_original"] = groupe.get("id")
        profil["rang_activite"] = rang
        profil["nom_groupe"] = f"Groupe {rang}"
        groupes.append(profil)

    communaute_assemblee = {
        **communaute,
        "communautes": groupes,
        "activite_temporelle": construire_activite_temporelle(dataset, groupes),
    }

    return {
        **donnees,
        "communaute": communaute_assemblee,
        "communautes": groupes,
    }


def dataframe_activite_communautes(donnees: dict) -> pd.DataFrame:
    communaute = donnees.get("communaute", {})
    groupes = communaute.get("communautes", [])
    activite = pd.DataFrame(communaute.get("activite_temporelle", []))
    if activite.empty:
        return activite

    noms_groupes = {}
    rangs_groupes = {}
    for index, groupe in enumerate(groupes, start=1):
        id_original = groupe.get("id_original", groupe.get("id", index))
        rang = groupe.get("rang_activite", index)
        nom = groupe.get("nom_groupe", f"Groupe {rang}")
        noms_groupes[id_original] = nom
        rangs_groupes[id_original] = rang

    if "nom_groupe" not in activite.columns:
        if "communaute" in activite.columns:
            activite["nom_groupe"] = (
                activite["communaute"]
                .map(noms_groupes)
                .fillna("Groupe " + activite["communaute"].astype(str))
            )
            activite["groupe"] = activite["communaute"].map(rangs_groupes).fillna(activite["communaute"])
        elif "groupe" in activite.columns:
            activite["nom_groupe"] = "Groupe " + activite["groupe"].astype(str)

    return activite


def afficher_analyse_semantique(donnees: dict, narratif: dict | None = None) -> None:
    narratif = narratif or donnees.get("narratif", {})
    if not narratif:
        st.info("Analyse sémantique non disponible.")
        return

    st.write(narratif.get("resume", ""))
    tonalite = narratif.get("tonalite", {})
    if tonalite:
        col1, col2, col3 = st.columns(3)
        col1.metric("Négatif", f"{tonalite.get('part_negative', 0)}%")
        col2.metric("Neutre", f"{tonalite.get('part_neutral', 0)}%")
        col3.metric("Positif", f"{tonalite.get('part_positive', 0)}%")

    corpus = narratif.get("corpus", {})
    if corpus:
        st.caption(
            f"Messages analysés: {corpus.get('messages_analyses')} / {corpus.get('messages_total')} "
            f"(doublons ignorés: {corpus.get('messages_ignores_car_doublons')})"
        )

    recits = narratif.get("recits", [])
    for recit in recits:
        titre = f"{recit['nom']} - risque {recit['niveau_risque']} ({recit['score_risque']})"
        with st.expander(titre):
            st.write(f"Volume: {recit['volume']} | % négatif: {recit['pct_negative']}")
            st.write(f"Mots clés: {', '.join(recit['mots_cles'])}")
            st.caption(recit["exemple"])


def afficher_focus_communautes(donnees: dict) -> None:
    communaute = donnees.get("communaute", {})
    groupes = communaute.get("communautes", [])
    if not groupes:
        st.info("Aucune communauté disponible.")
        return

    activite = dataframe_activite_communautes(donnees)
    if activite.empty:
        st.info("Activité temporelle non disponible.")
    else:
        fig = px.line(
            activite,
            x="Date",
            y="messages",
            color="nom_groupe",
            title="Répartition de l'activité des communautés dans le temps",
        )
        fig.update_layout(legend_title_text="Communautés", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    choix = st.selectbox(
        "Communauté à décrypter",
        options=[g["rang_activite"] for g in groupes],
        format_func=lambda rang: f"Groupe {rang}",
        key="focus_communaute",
    )
    groupe = next(g for g in groupes if g["rang_activite"] == choix)
    narratif = groupe.get("narratif", {})
    resume = narratif.get("resume", "Narratif non disponible pour ce groupe.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        carte_indicateur("Messages", groupe.get("nombre_messages", 0), "Activité du groupe", "#1266f1")
    with col2:
        carte_indicateur("Membres", groupe.get("nombre_retweeteurs", 0), "Comptes mobilisés", "#00a878")
    with col3:
        carte_indicateur("Followers", groupe.get("followers_total", 0), "Audience potentielle", "#ef476f")
    with col4:
        carte_indicateur("Négatif", f"{groupe.get('pct_negative', 0)}%", "Tonalité à surveiller", "#f59e0b")

    sources = ", ".join(sources_pivots_liste(groupe)) or "Sources non disponibles"
    carte_message(
        f"Groupe {choix} - narratif dominant",
        f"Sources pivots: {sources}",
        resume,
        "#6d5dfc",
    )


def afficher_communautes_detail(donnees: dict) -> None:
    communaute = donnees.get("communaute", {})
    groupes = communaute.get("communautes", [])
    if not groupes:
        st.info("Aucune communauté disponible.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Détectées", communaute.get("nombre_communautes_detectees"))
    col2.metric("Retenues", len(groupes))
    col3.metric("Modularité", communaute.get("modularite"))
    col4.metric("Seuil messages", communaute.get("seuil_messages"))

    choix = st.selectbox(
        "Sélectionner un groupe",
        options=[g["rang_activite"] for g in groupes],
        format_func=lambda rang: f"Groupe {rang}",
        key="communaute_detail",
    )
    groupe = next(g for g in groupes if g["rang_activite"] == choix)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Messages", groupe.get("nombre_messages"))
    col2.metric("Retweeteurs", groupe.get("nombre_retweeteurs"))
    col3.metric("Followers total", groupe.get("followers_total"))
    col4.metric("% négatif", f"{groupe.get('pct_negative')}%")

    col1, col2, col3 = st.columns(3)
    col1.metric("Auteurs", groupe.get("nombre_auteurs"))
    col2.metric("Comptes vérifiés", groupe.get("comptes_verifies"))
    col3.metric("% vérifiés", f"{groupe.get('pct_verified')}%")

    st.write("Sources pivots:", groupe.get("sources_pivots", []))
    if groupe.get("compte_influent"):
        st.write("Compte le plus influent:", groupe["compte_influent"])

    afficher_analyse_semantique(donnees, groupe.get("narratif", {}))


def afficher_onglet_communautes(donnees: dict, detail: bool = False) -> None:
    injecter_style_communautes()
    st.subheader("Communautés")
    st.markdown(
        '<div class="section-lead">Lecture des groupes d’amplification, de leur activité et de leurs narratifs dominants.</div>',
        unsafe_allow_html=True,
    )
    if detail:
        afficher_communautes_detail(donnees)
    else:
        afficher_focus_communautes(donnees)


def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    donnees_assemblees = assembler_communautes(donnees)
    communaute = donnees_assemblees.get("communaute", {})
    communautes = donnees_assemblees.get("communautes", [])

    afficher_contrat_agent(
        "Brique coordination - qui amplifie ensemble ?",
        "Coordination / polarisation",
        [
            "Retweets avec Author et _source.",
            "Sources relayées au moins 10 fois.",
            "Graphe biparti retweeteur <-> source amplifiée.",
            "Dataset assemblé par groupe pour enrichir l'audience, les auteurs et l'activité.",
        ],
        [
            "Construction d'un graphe NetworkX pondéré.",
            "Détection de communautés par algorithme de Louvain.",
            "Calcul de modularité.",
            "Assemblage des groupes avec activité temporelle, followers, comptes vérifiés et narratif.",
        ],
        {
            "Communautés": len(communautes),
            "Modularité": communaute.get("modularite", "n/a") if isinstance(communaute, dict) else "n/a",
            "Auteurs": communaute.get("nombre_auteurs_communautarises", "n/a") if isinstance(communaute, dict) else "n/a",
        },
        [
            "Groupes d'amplification classés par activité.",
            "Sources pivots et compte influent par groupe.",
            "Narratif dominant et tonalité par communauté.",
        ],
    )

    afficher_onglet_communautes(donnees_assemblees, detail=False)
