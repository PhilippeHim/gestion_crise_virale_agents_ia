from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st


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
    if valeur is None or pd.isna(valeur):
        return "n/a"
    try:
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
            activite["groupe"] = (
                activite["communaute"]
                .map(rangs_groupes)
                .fillna(activite["communaute"])
            )
        elif "groupe" in activite.columns:
            activite["nom_groupe"] = "Groupe " + activite["groupe"].astype(str)

    return activite


def afficher_focus_communautes(donnees: dict) -> None:
    communaute = donnees.get("communaute", {})
    groupes = communaute.get("communautes", [])
    if not groupes:
        st.info("Aucune communaute disponible.")
        return

    activite = dataframe_activite_communautes(donnees)
    if activite.empty:
        st.info("Activite temporelle non disponible.")
    else:
        fig = px.line(
            activite,
            x="Date",
            y="messages",
            color="nom_groupe",
            title="Repartition de l'activite des communautes dans le temps",
        )
        fig.update_layout(legend_title_text="Communautes", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    choix = st.selectbox(
        "Communaute a decrypter",
        options=[g["rang_activite"] for g in groupes],
        format_func=lambda rang: f"Groupe {rang}",
        key="focus_communaute",
    )
    groupe = next(g for g in groupes if g["rang_activite"] == choix)
    narratif = groupe.get("narratif", {})
    resume = narratif.get("resume", "Narratif non disponible pour ce groupe.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        carte_indicateur("Messages", groupe.get("nombre_messages", 0), "Activite du groupe", "#1266f1")
    with col2:
        carte_indicateur("Membres", groupe.get("nombre_retweeteurs", 0), "Comptes mobilises", "#00a878")
    with col3:
        carte_indicateur("Followers", groupe.get("followers_total", 0), "Audience potentielle", "#ef476f")
    with col4:
        carte_indicateur("Negatif", f"{groupe.get('pct_negative', 0)}%", "Tonalite dominante a surveiller", "#f59e0b")

    sources = ", ".join(source for source, _ in groupe.get("sources_pivots", [])) or "Sources non disponibles"
    carte_message(
        f"Groupe {choix} - narratif dominant",
        f"Sources pivots: {sources}",
        resume,
        "#6d5dfc",
    )


def afficher_analyse_semantique(donnees: dict, narratif: dict | None = None) -> None:
    narratif = narratif or donnees.get("narratif", {})
    if not narratif:
        st.info("Analyse semantique non disponible.")
        return

    st.write(narratif.get("resume", ""))
    tonalite = narratif.get("tonalite", {})
    if tonalite:
        col1, col2, col3 = st.columns(3)
        col1.metric("Negatif", f"{tonalite.get('part_negative', 0)}%")
        col2.metric("Neutre", f"{tonalite.get('part_neutral', 0)}%")
        col3.metric("Positif", f"{tonalite.get('part_positive', 0)}%")

    corpus = narratif.get("corpus", {})
    if corpus:
        st.caption(
            f"Messages analyses: {corpus.get('messages_analyses')} / {corpus.get('messages_total')} "
            f"(doublons ignores: {corpus.get('messages_ignores_car_doublons')})"
        )

    recits = narratif.get("recits", [])
    for recit in recits:
        with st.expander(f"{recit['nom']} - risque {recit['niveau_risque']} ({recit['score_risque']})"):
            st.write(f"Volume: {recit['volume']} | % negatif: {recit['pct_negative']}")
            st.write(f"Mots cles: {', '.join(recit['mots_cles'])}")
            st.caption(recit["exemple"])


def afficher_communautes(donnees: dict) -> None:
    communaute = donnees.get("communaute", {})
    groupes = communaute.get("communautes", [])
    if not groupes:
        st.info("Aucune communaute disponible.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Detectees", communaute.get("nombre_communautes_detectees"))
    col2.metric("Retenues", len(groupes))
    col3.metric("Modularite", communaute.get("modularite"))
    col4.metric("Seuil messages", communaute.get("seuil_messages"))

    activite = dataframe_activite_communautes(donnees)
    if not activite.empty:
        fig = px.line(
            activite,
            x="Date",
            y="messages",
            color="nom_groupe",
            title="Activite des groupes dans le temps",
        )
        st.plotly_chart(fig, use_container_width=True)
        pics = activite.sort_values("messages", ascending=False).head(5)
        st.caption(
            "Pics principaux: "
            + ", ".join(
                f"{row.nom_groupe} le {row.Date} ({int(row.messages)} messages)"
                for row in pics.itertuples()
            )
        )

    choix = st.selectbox(
        "Selectionner un groupe",
        options=[g["rang_activite"] for g in groupes],
        format_func=lambda rang: f"Groupe {rang}",
        key="communaute_detail",
    )
    groupe = next(g for g in groupes if g["rang_activite"] == choix)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Messages", groupe["nombre_messages"])
    col2.metric("Retweeteurs", groupe["nombre_retweeteurs"])
    col3.metric("Followers total", groupe["followers_total"])
    col4.metric("% negatif", f"{groupe['pct_negative']}%")

    col1, col2, col3 = st.columns(3)
    col1.metric("Auteurs", groupe["nombre_auteurs"])
    col2.metric("Comptes verifies", groupe["comptes_verifies"])
    col3.metric("% verifies", f"{groupe['pct_verified']}%")

    st.write("Sources pivots:", groupe["sources_pivots"])
    if groupe.get("compte_influent"):
        st.write("Compte le plus influent:", groupe["compte_influent"])

    afficher_analyse_semantique(donnees, groupe.get("narratif", {}))


def afficher_onglet_communautes(donnees: dict, detail: bool = False) -> None:
    injecter_style_communautes()
    st.subheader("Communautes")
    st.markdown(
        '<div class="section-lead">Lecture des groupes d amplification, de leur activite et de leurs narratifs dominants.</div>',
        unsafe_allow_html=True,
    )
    if detail:
        afficher_communautes(donnees)
    else:
        afficher_focus_communautes(donnees)
