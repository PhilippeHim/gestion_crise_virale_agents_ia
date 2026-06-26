import json
import os
import urllib.error
import urllib.request

import pandas as pd
import streamlit as st
from pipeline.config import config

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *


def normaliser_json(value):
    if isinstance(value, dict):
        return {str(cle): normaliser_json(contenu) for cle, contenu in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [normaliser_json(contenu) for contenu in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        return normaliser_json(value.item())
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _records(dataframe: pd.DataFrame, colonnes: list[str], limit: int = 5) -> list[dict]:
    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        return []
    disponibles = [colonne for colonne in colonnes if colonne in dataframe.columns]
    if not disponibles:
        return []
    return normaliser_json(dataframe[disponibles].head(limit).to_dict("records"))


def construire_json_llm(donnees: dict) -> dict:
    dataset = donnees.get("dataset")
    narratif = donnees.get("narratif", {}) if isinstance(donnees.get("narratif"), dict) else {}
    proposition = donnees.get("proposition", {}) if isinstance(donnees.get("proposition"), dict) else {}
    concentration = donnees.get("concentration", {}) if isinstance(donnees.get("concentration"), dict) else {}
    communaute = donnees.get("communaute", {}) if isinstance(donnees.get("communaute"), dict) else {}
    communautes = donnees.get("communautes", [])
    amplificateurs = donnees.get("amplificateurs")
    alerte = etat_alerte_trigger_volume(donnees)

    acteurs = {}
    viralite = {}
    propagation = {
        "alerte_volume": alerte,
        "concentration": concentration,
        "top_amplificateurs": _records(amplificateurs, ["source", "retweets", "part_pct"], 5),
        "pic": proposition.get("chiffres_cles", {}).get("pic", {}),
    }

    if isinstance(dataset, pd.DataFrame) and not dataset.empty:
        acteurs = {
            "messages": int(len(dataset)),
            "auteurs_uniques": int(dataset["Author"].nunique()) if "Author" in dataset.columns else None,
            "top_auteurs": (
                dataset["Author"].fillna("inconnu").value_counts().head(8).astype(int).to_dict()
                if "Author" in dataset.columns
                else {}
            ),
            "comptes_certifies": (
                int(pd.Series(dataset["X Verified"]).fillna(False).astype(bool).sum())
                if "X Verified" in dataset.columns
                else None
            ),
        }
        if "Classe_viralite" in dataset.columns:
            viralite = {
                "classes": dataset["Classe_viralite"].fillna("Non classé").value_counts().astype(int).to_dict(),
                "score_max": (
                    round(float(pd.to_numeric(dataset["Viralite"], errors="coerce").max()), 3)
                    if "Viralite" in dataset.columns
                    else None
                ),
                "top_contenus_viraux": _records(
                    dataset.sort_values("Viralite", ascending=False) if "Viralite" in dataset.columns else dataset,
                    ["Author", "Classe_viralite", "Viralite", "Reach", "Impressions", "Full Text"],
                    3,
                ),
            }

    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
    recits_llm = [
        {
            "nom": recit.get("nom"),
            "mots_cles": recit.get("mots_cles", [])[:6],
            "volume": recit.get("volume"),
            "pct_negative": recit.get("pct_negative"),
            "score_risque": recit.get("score_risque"),
            "niveau_risque": recit.get("niveau_risque"),
            "observation": recit.get("exemple"),
        }
        for recit in recits[:6]
    ]

    payload = {
        "objectif_llm": "Produire une réponse publique sobre pour dégonfler une crise informationnelle.",
        "contraintes_reponse": [
            "ne pas attaquer de personne ou de compte",
            "ne pas reprendre les formulations polémiques",
            "rester factuel, court et vérifiable",
            "inclure des placeholders si des faits internes manquent",
            "soumettre à validation direction et juridique avant publication",
        ],
        "agent_viralite_acteurs": {
            "acteurs": acteurs,
            "viralite": viralite,
        },
        "recits_narration_6_observations": recits_llm,
        "propagation": propagation,
        "coordination": {
            "resume": {
                "modularite": communaute.get("modularite"),
                "communautes_retenues": len(communautes),
                "auteurs_communautarises": communaute.get("nombre_auteurs_communautarises"),
            },
            "communautes": [
                {
                    "id": item.get("id"),
                    "nombre_messages": item.get("nombre_messages"),
                    "nombre_retweeteurs": item.get("nombre_retweeteurs"),
                    "sources_pivots": item.get("sources_pivots", [])[:3],
                    "pct_negative": item.get("pct_negative"),
                    "pct_verified": item.get("pct_verified"),
                    "jour_pic": item.get("jour_pic"),
                }
                for item in communautes[:5]
            ],
        },
        "semantique": {
            "tonalite": narratif.get("tonalite", {}),
            "corpus": narratif.get("corpus", {}),
            "resume": narratif.get("resume"),
            "recit_prioritaire": proposition.get("recit_prioritaire", {}),
        },
    }
    return normaliser_json(payload)


def construire_prompt_llm(payload: dict) -> str:
    payload_json = json.dumps(normaliser_json(payload), ensure_ascii=False, indent=2, default=str)
    return (
        "Tu es un conseiller en communication de crise. À partir du JSON suivant, analyse les 6 récits "
        "de narration disponibles, identifie les 3 récits les plus impactants selon le score de risque, "
        "la part négative et le volume, puis génère 3 réponses publiques distinctes pour dégonfler la crise. "
        "Ensuite, construis un brouillon final unique en fusionnant les 3 sorties précédentes. "
        "Le brouillon final doit être publiable après validation humaine : court, lisible par une direction "
        "de communication, factuel, apaisant, sans attaque personnelle et sans reprendre les formulations polémiques. "
        "Format attendu :\n"
        "Sorties intermédiaires LLM\n"
        "1. Récit ciblé : ...\n"
        "   Réponse proposée : ...\n"
        "   Point à valider : ...\n"
        "2. ...\n"
        "3. ...\n\n"
        "Brouillon final consolidé\n"
        "[texte final construit à partir des 3 réponses précédentes]\n\n"
        "Points de validation humaine\n"
        "- ...\n\n"
        f"JSON d'entrée:\n{payload_json}"
    )


def recits_impactants(payload: dict, limite: int = 3) -> list[dict]:
    recits = payload.get("recits_narration_6_observations", [])
    return sorted(
        recits,
        key=lambda recit: (
            recit.get("score_risque") or 0,
            recit.get("pct_negative") or 0,
            recit.get("volume") or 0,
        ),
        reverse=True,
    )[:limite]


def generer_reponse_degonflage(payload: dict) -> str:
    semantique = payload.get("semantique", {})
    propagation = payload.get("propagation", {})
    coordination = payload.get("coordination", {}).get("resume", {})
    recits = recits_impactants(payload, 3)

    communautes = coordination.get("communautes_retenues", "n/a")
    pic = propagation.get("pic", {})
    tonalite_globale = semantique.get("tonalite", {}).get("part_negative", "n/a")

    lignes = []
    for index, recit in enumerate(recits, start=1):
        recit_nom = recit.get("nom") or f"récit {index}"
        pct_negative = recit.get("pct_negative") or tonalite_globale
        reponse = (
            "Nous avons identifié une inquiétude récurrente autour de ce sujet. "
            f"Les échanges liés à ce récit présentent une tonalité négative estimée à {pct_negative}%. "
            "Notre réponse doit rester factuelle : rappeler le cadre, préciser les éléments vérifiés "
            "et éviter toute personnalisation du débat."
        )
        lignes.append(
            f"{index}. Récit ciblé : {recit_nom}\n"
            f"   Réponse proposée : {reponse} Le pic du {pic.get('date', 'n/a')} et "
            f"les {communautes} communautés observées appellent une clarification sobre, pas une riposte.\n"
            "   Point à valider : fait interne validé, position officielle et validation juridique."
        )

    if not lignes:
        return (
            "Aucun récit exploitable n'est disponible pour générer les 3 réponses prioritaires."
        )

    brouillon_final = (
        "Nous avons pris connaissance des réactions et des interrogations exprimées autour de ce sujet. "
        "Les analyses font apparaître plusieurs récits qui appellent une réponse claire, factuelle et apaisée. "
        "Notre position doit rappeler le cadre de décision, préciser les éléments vérifiés et éviter toute mise en cause "
        "personnelle. [Fait interne validé à insérer]. [Position institutionnelle officielle à préciser]. "
        f"Compte tenu du pic observé le {pic.get('date', 'n/a')} et de la structuration en {communautes} communautés, "
        "la priorité est d'apporter une clarification sobre, sans alimenter la polémique. "
        "Ce message doit être validé par la direction et le juridique avant toute publication."
    )

    return (
        "Sorties intermédiaires LLM\n\n"
        + "\n\n".join(lignes)
        + "\n\nBrouillon final consolidé\n\n"
        + brouillon_final
        + "\n\nPoints de validation humaine\n"
        "- Faits internes validés.\n"
        "- Position officielle de l'institution.\n"
        "- Validation direction et juridique."
    )


def cle_gemini() -> str | None:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY") or config("GEMINI_API_KEY", default=None)


def appeler_gemini(prompt: str) -> tuple[str, str]:
    api_key = cle_gemini()
    if not api_key:
        return "", "Clé Gemini absente : définis GEMINI_API_KEY dans .env, Streamlit secrets ou ton shell."

    modele = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent?key={api_key}"
    corps = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.35,
            "topP": 0.9,
            "maxOutputTokens": 900,
        },
    }
    requete = urllib.request.Request(
        url,
        data=json.dumps(corps).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(requete, timeout=30) as reponse:
            resultat = json.loads(reponse.read().decode("utf-8"))
    except urllib.error.HTTPError as erreur:
        detail = erreur.read().decode("utf-8", errors="ignore")
        return "", f"Erreur Gemini HTTP {erreur.code} : {detail[:500]}"
    except urllib.error.URLError as erreur:
        return "", f"Gemini inaccessible : {erreur.reason}"
    except TimeoutError:
        return "", "Gemini inaccessible : délai dépassé."

    candidats = resultat.get("candidates", [])
    if not candidats:
        return "", f"Gemini n'a renvoyé aucun candidat exploitable : {resultat}"

    morceaux = candidats[0].get("content", {}).get("parts", [])
    texte = "\n".join(part.get("text", "") for part in morceaux if part.get("text")).strip()
    if not texte:
        return "", f"Réponse Gemini vide : {resultat}"
    return texte, "Réponse générée par Gemini."


def extraire_brouillon_consolide(texte_llm: str) -> str:
    marqueur = "Brouillon final consolidé"
    if marqueur not in texte_llm:
        return texte_llm.strip()

    apres_marqueur = texte_llm.split(marqueur, 1)[1].strip()
    for separateur in ["Points de validation humaine", "Points de validation"]:
        if separateur in apres_marqueur:
            return apres_marqueur.split(separateur, 1)[0].strip()
    return apres_marqueur


def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    proposition = donnees.get("proposition", {})
    payload_llm = construire_json_llm(donnees)
    prompt_llm = construire_prompt_llm(payload_llm)
    reponse_gemini, statut_gemini = appeler_gemini(prompt_llm)
    reponse_llm = reponse_gemini or generer_reponse_degonflage(payload_llm)
    recits_selectionnes = recits_impactants(payload_llm, 3)
    brouillon_consolide = extraire_brouillon_consolide(reponse_llm)

    afficher_contrat_agent(
        "Proposition finale - reformulation, réponse et validation",
        "Proposition / décision",
        [
            "Récit prioritaire issu du filtre de risque.",
            "Tonalité, concentration, amplificateurs et niveau de risque.",
            "Messages clés, points à valider et messages à éviter.",
            "Contraintes : neutralité, prudence, validation humaine.",
        ],
        [
            "Transformation des signaux techniques en diagnostic éditorial.",
            "Choix d'une stratégie de réponse adaptée au risque.",
            "Rédaction d'un brouillon factuel et vérifiable.",
            "Contrôle humain obligatoire avant publication.",
        ],
        {
            "Stratégie": proposition.get("strategie", "n/a"),
            "Risque": proposition.get("niveau_risque", "n/a"),
            "Priorité": proposition.get("priorite", "n/a"),
            "Brouillon": "Consolidé LLM" if brouillon_consolide else "n/a",
            "Messages clés": len(proposition.get("messages_cles", [])),
            "Validation": "Obligatoire",
        },
        [
            "Diagnostic reformulé pour décideur.",
            "Brouillon de réponse non publiable sans validation.",
            "Décision humaine : publier, modifier ou ignorer.",
        ],
    )

    st.markdown("**Synthèse exécutive préparée**")
    st.write(proposition.get("synthese_executive", "Synthèse non disponible."))

    st.markdown("**Mécanique LLM**")
    st.caption(
        "Le LLM reçoit les 6 récits narratifs, les signaux acteurs/viralité, propagation, "
        "coordination et sémantique. Le JSON technique est masqué dans l'interface."
    )
    if recits_selectionnes:
        st.markdown("**3 récits les plus impactants retenus**")
        for recit in recits_selectionnes:
            st.write(
                f"- **{recit.get('nom', 'Récit sans nom')}** · "
                f"risque {recit.get('score_risque', 'n/a')} · "
                f"{recit.get('volume', 'n/a')} messages · "
                f"{recit.get('pct_negative', 'n/a')}% nég."
            )

    st.markdown("**Sorties LLM et brouillon final**")
    if reponse_gemini:
        st.success(statut_gemini)
    else:
        st.warning(f"{statut_gemini} Réponse locale affichée en secours.")
    st.text_area("3 sorties LLM puis brouillon consolidé", value=reponse_llm, height=360)

    st.markdown("**Brouillon central consolidé**")
    st.text_area("Brouillon final proposé", value=brouillon_consolide, height=220)

    col_eviter, col_valider = st.columns(2)
    with col_eviter:
        st.markdown("**À éviter**")
        for item in proposition.get("messages_a_eviter", []):
            st.write(f"- {item}")
    with col_valider:
        st.markdown("**À valider**")
        for item in proposition.get("points_a_valider", []):
            st.write(f"- {item}")
