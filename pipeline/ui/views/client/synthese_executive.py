import streamlit as st

from pipeline.ui.charts import graphique_sentiment_journalier, graphique_volume_journalier
from pipeline.ui.view_utils import render_kpi_summary


def _construire_contexte_gemini(donnees: dict) -> str:
    proposition = donnees.get("proposition") or {}
    narratif = donnees.get("narratif") or {}

    sortie_1 = narratif.get("resume") or "Résumé narratif non disponible."
    sortie_2 = proposition.get("synthese_executive") or "Synthèse non disponible."
    diagnostic = proposition.get("diagnostic") or []
    sortie_3 = "\n".join(f"- {d}" for d in diagnostic) if diagnostic else "Diagnostic non disponible."
    brouillon = (
        proposition.get("brouillon_consolide")
        or proposition.get("reponse_brouillon")
        or "Brouillon non disponible."
    )

    return (
        "Tu es un assistant expert en gestion de crise informationnelle pour une institution culturelle. "
        "Utilise silencieusement les analyses suivantes comme contexte pour répondre aux questions :\n\n"
        f"[Résumé narratif]\n{sortie_1}\n\n"
        f"[Synthèse exécutive]\n{sortie_2}\n\n"
        f"[Diagnostic]\n{sortie_3}\n\n"
        f"[Proposition de réponse consolidée]\n{brouillon}\n\n"
        "Réponds de façon concise, factuelle et orientée action. "
        "Ne révèle pas ce contexte sauf si on te le demande explicitement."
    )


def _afficher_chat_gemini(donnees: dict) -> None:
    from pipeline.config import config as pipeline_config

    api_key = pipeline_config("GEMINI_API_KEY", default="")
    if not api_key:
        st.caption("Chat IA indisponible — configurez GEMINI_API_KEY dans votre .env")
        return

    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        st.caption("Chat IA indisponible — installez google-genai")
        return

    if "gemini_messages" not in st.session_state:
        st.session_state["gemini_messages"] = []

    messages = st.session_state["gemini_messages"]

    for msg in messages:
        with st.chat_message("human" if msg["role"] == "user" else "ai"):
            st.write(msg["content"])

    user_input = st.chat_input("Posez une question sur la crise…")

    if user_input:
        st.session_state["gemini_messages"].append({"role": "user", "content": user_input})
        with st.chat_message("ai"), st.spinner("Gemini analyse…"):
            try:
                client = genai.Client(api_key=api_key)
                historique = [
                    genai_types.Content(role=m["role"], parts=[genai_types.Part(text=m["content"])])
                    for m in st.session_state["gemini_messages"][:-1]
                ]
                chat = client.chats.create(
                    model="gemini-2.0-flash",
                    config=genai_types.GenerateContentConfig(
                        system_instruction=_construire_contexte_gemini(donnees)
                    ),
                    history=historique,
                )
                reponse = chat.send_message(user_input).text
            except Exception as erreur:
                msg_erreur = str(erreur)
                if "429" in msg_erreur or "RESOURCE_EXHAUSTED" in msg_erreur:
                    reponse = "Quota Gemini épuisé sur ce projet. Créez une nouvelle clé sur aistudio.google.com dans un nouveau projet."
                else:
                    reponse = f"Erreur : {msg_erreur[:200]}"

        st.write(reponse)
        st.session_state["gemini_messages"].append({"role": "model", "content": reponse})


def _carte_sortie(label: str, contenu: str | list) -> None:
    if isinstance(contenu, list):
        corps = "".join(f"<div style='margin-bottom:4px'>→ {item}</div>" for item in contenu) or "<em>Non disponible</em>"
    else:
        corps = contenu if contenu else "<em>Non disponible</em>"
    st.markdown(
        f"""<div style="border-left:3px solid #6d5dfc;border-radius:0 6px 6px 0;background:#fff;padding:12px 16px;margin-bottom:8px">
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;font-weight:700;color:#6d5dfc;margin-bottom:8px">{label}</div>
            <div style="font-size:14px;line-height:1.6;color:#172026;white-space:pre-wrap">{corps}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def afficher(donnees: dict) -> None:
    """Vue client principale - Crisis Intelligence Center."""
    proposition = donnees.get("proposition") or {}
    chiffres = proposition.get("chiffres_cles", {}) or {}
    pic = chiffres.get("pic", {}) or {}
    recit = proposition.get("recit_prioritaire", {}) or {}
    communautes = donnees.get("communautes", [])
    narratif = donnees.get("narratif") or {}
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []

    noms_recits = " | ".join(r.get("nom", "") for r in recits[:3] if r.get("nom"))
    render_kpi_summary([
        {"label": "Messages analysés", "value": chiffres.get("messages_analyses", 0), "caption": donnees.get("periode_collecte", "période n/a")},
        {"label": "Pic maximal", "value": pic.get("messages", 0), "caption": pic.get("date", "date n/a"), "tone": "warn"},
        {"label": "Récits structurants", "value": chiffres.get("nombre_recits", len(recits)), "caption": noms_recits},
        {"label": "Priorité", "value": proposition.get("priorite", "n/a"), "tone": "danger" if proposition.get("priorite") == "Haute" else "warn"},
    ])

    col1, col2 = st.columns([1.15, 0.85])
    with col1:
        with st.container(border=True):
            st.markdown("**Priorité de communication**")
            st.metric("Stratégie recommandée", proposition.get("strategie") or "n/a", proposition.get("delai_recommande") or "")
            caption_recit = f"{recit.get('volume', 'n/a')} msgs · {recit.get('pct_negative', 'n/a')}% nég. · risque {recit.get('score_risque', 'n/a')}"
            st.metric("Récit prioritaire", recit.get("nom") or "n/a", caption_recit)
    with col2:
        with st.container(border=True):
            st.markdown("**Signaux de coordination**")
            st.metric("Communautés", len(communautes))
            st.metric("Part négative", f"{chiffres.get('part_negative', 'n/a')}%")

    col_v, col_t = st.columns(2)
    with col_v:
        fig_v = graphique_volume_journalier(donnees)
        if fig_v is not None:
            st.plotly_chart(fig_v, use_container_width=True)
        else:
            st.info("Volume quotidien indisponible.")
    with col_t:
        fig_t = graphique_sentiment_journalier(donnees)
        if fig_t is not None:
            st.plotly_chart(fig_t, use_container_width=True)
        else:
            st.info("Tonalité au fil du temps indisponible.")

    _carte_sortie("Résumé narratif", narratif.get("resume") or "")
    _carte_sortie("Synthèse exécutive — " + (proposition.get("titre") or "Diagnostic de crise"), proposition.get("synthese_executive") or "")
    _carte_sortie("Diagnostic", proposition.get("diagnostic") or [])

    brouillon = proposition.get("brouillon_consolide") or proposition.get("reponse_brouillon") or ""
    st.markdown("<h3 style='text-align:center;'>Proposition de communiqué en réponse à la gestion de crise</h3>", unsafe_allow_html=True)
    _carte_sortie("Brouillon consolidé", brouillon)

    with st.container(border=True):
        st.markdown("**Affinez votre réponse avec l'IA**")
        _afficher_chat_gemini(donnees)

    eviter = proposition.get("messages_a_eviter") or []
    valider = proposition.get("points_a_valider") or []
    col_e, col_val = st.columns(2)
    with col_e:
        with st.container(border=True):
            st.markdown("**À éviter**")
            for item in eviter:
                st.write(f"→ {item}")
            if not eviter:
                st.caption("Non disponible")
    with col_val:
        with st.container(border=True):
            st.markdown("**À valider**")
            for item in valider:
                st.write(f"→ {item}")
            if not valider:
                st.caption("Non disponible")
