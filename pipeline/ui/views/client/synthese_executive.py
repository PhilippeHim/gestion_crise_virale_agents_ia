import streamlit as st

from pipeline.ui.charts import graphique_sentiment_journalier, graphique_volume_journalier
from pipeline.ui.react_components import render_react_summary


def _construire_contexte_gemini(donnees: dict) -> str:
    proposition = donnees.get("proposition") or {}
    narratif = donnees.get("narratif") or {}

    sortie_1 = narratif.get("resume") or "Résumé narratif non disponible."
    sortie_2 = proposition.get("synthese_executive") or "Synthèse non disponible."
    diagnostic = proposition.get("diagnostic") or []
    sortie_3 = "\n".join(f"- {d}" for d in diagnostic) if diagnostic else "Diagnostic non disponible."
    brouillon = proposition.get("reponse_brouillon") or "Brouillon non disponible."

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
    render_react_summary([
        {"label": "Messages analysés", "value": chiffres.get("messages_analyses", 0), "caption": donnees.get("periode_collecte", "période n/a")},
        {"label": "Pic maximal", "value": pic.get("messages", 0), "caption": pic.get("date", "date n/a"), "tone": "warn"},
        {"label": "Récits structurants", "value": chiffres.get("nombre_recits", len(recits)), "caption": noms_recits},
        {"label": "Priorité", "value": proposition.get("priorite", "n/a"), "tone": "danger" if proposition.get("priorite") == "Haute" else "warn"},
    ])

    with st.container(border=True):
        st.subheader(proposition.get("titre") or "Diagnostic de crise")
        st.write(proposition.get("synthese_executive") or "Synthèse non disponible.")

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

    brouillon = proposition.get("reponse_brouillon") or ""
    st.markdown("<h3 style='text-align:center;'>Proposition de communiqué en réponse à la gestion de crise</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        st.write(brouillon if brouillon else "Proposition non disponible.")

    with st.container(border=True):
        st.markdown("**Chat — Analyste IA**")
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
