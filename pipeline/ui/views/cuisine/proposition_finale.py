import json
import os
import re
import http.client
import hashlib
import urllib.error
import urllib.request
from html import escape

import pandas as pd
import streamlit as st
from pipeline.config import config

from pipeline.ui.charts import *
from pipeline.ui.view_utils import *


FOURNISSEUR_LLM_DEFAUT = "Google Gemini"
FOURNISSEURS_LLM = {
    "Google Gemini": {
        "env": "GEMINI_API_KEY",
        "modeles": ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash", "gemini-2.5-pro"],
    },
    "OpenAI": {
        "env": "OPENAI_API_KEY",
        "modeles": ["gpt-4.1-mini", "gpt-4o-mini", "gpt-4.1", "gpt-4o"],
    },
    "Anthropic Claude": {
        "env": "ANTHROPIC_API_KEY",
        "modeles": ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest", "claude-3-opus-latest"],
    },
    "Mistral AI": {
        "env": "MISTRAL_API_KEY",
        "modeles": ["mistral-small-latest", "mistral-medium-latest", "mistral-large-latest"],
    },
}
MODELE_GEMINI_DEFAUT = FOURNISSEURS_LLM["Google Gemini"]["modeles"][0]
MODELES_GEMINI_REPLI = FOURNISSEURS_LLM["Google Gemini"]["modeles"][1:]
MODELES_GEMINI_OBSOLETES = {"gemini-1.5-flash", "gemini-1.5-pro"}
QUESTION_EDITORIALE_DEFAUT = (
    "Au regard des signaux observés, quelle posture éditoriale recommandes-tu pour répondre clairement aux accusations "
    "sans amplifier la crise ? Monte la défense d'un cran : faut-il contextualiser, rectifier, opposer un démenti ferme "
    "ou reconnaître une inquiétude tout en contestant les raccourcis ? Quels points issus des 3 analyses brutes doivent "
    "être traités explicitement, quels cadrages doivent être refusés, quels termes doivent être évités, et quel niveau "
    "de fermeté est adapté pour un rédacteur en chef ou une direction de communication ?"
)


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
            "id": recit.get("id"),
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
    exemples_dataset_par_recit = {}
    if isinstance(dataset, pd.DataFrame) and not dataset.empty:
        colonne_texte = next(
            (colonne for colonne in ["message_normalizer", "Full Text"] if colonne in dataset.columns),
            None,
        )
        if colonne_texte:
            textes = dataset[colonne_texte].fillna("").astype(str)
            for recit in recits_llm:
                mots = sorted(
                    _mots_recit(
                        " ".join(
                            [
                                str(recit.get("nom", "")),
                                " ".join(str(mot) for mot in recit.get("mots_cles", [])),
                            ]
                        )
                    )
                )
                if not mots:
                    continue
                motif = "|".join(re.escape(mot) for mot in mots[:10])
                candidats = textes[textes.str.contains(motif, case=False, na=False, regex=True)]
                exemples_dataset_par_recit[str(recit.get("id"))] = [
                    nettoyer_sortie_llm(texte) for texte in candidats.drop_duplicates().head(10).tolist()
                ]
    exemples_rag_par_recit = (
        narratif.get("rag", {}).get("exemples_par_recit", {})
        if isinstance(narratif.get("rag"), dict)
        else {}
    )
    for recit in recits_llm:
        recit_id = str(recit.get("id"))
        exemples_tweets = [
            nettoyer_sortie_llm(item.get("message", ""))
            for item in exemples_rag_par_recit.get(recit_id, [])
            if item.get("message")
        ]
        exemples_tweets.extend(exemples_dataset_par_recit.get(recit_id, []))
        recit["cluster_id"] = recit.get("id")
        recit["volume_messages"] = recit.get("volume")
        recit["sentiment_moyen"] = recit.get("pct_negative")
        recit["date_pic"] = propagation.get("pic", {}).get("date")
        recit["nombre_communautes"] = len(communautes)
        recit["exemples_tweets"] = list(dict.fromkeys(exemples_tweets))[:10]

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
        "rag": narratif.get("rag", {}),
        "exemples_dataset_par_recit": exemples_dataset_par_recit,
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


def consigne_reponse_finale() -> str:
    return st.session_state.get("prompt_reponse_finale_llm", QUESTION_EDITORIALE_DEFAUT)


def construire_prompt_llm(payload: dict) -> str:
    payload_json = json.dumps(normaliser_json(payload), ensure_ascii=False, indent=2, default=str)
    question_editoriale = consigne_reponse_finale()
    return (
        "Tu es analyste d'une crise informationnelle. À partir du JSON suivant, analyse les 6 récits "
        "de narration disponibles et identifie les 3 récits les plus impactants selon le score de risque, "
        "la part négative, le volume et les exemples de tweets associés. "
        "Les blocs SORTIE_LLM_1 à SORTIE_LLM_3 doivent être des observations analytiques brutes, "
        "descriptives, factuelles et différenciées. Ils ne doivent pas proposer de stratégie de réponse, "
        "ne doivent pas adopter le ton d'un service communication et ne doivent pas défendre l'organisation. "
        "Distingue clairement ce qui est observé dans les tweets, ce qui relève d'une hypothèse d'interprétation "
        "et ce qui doit être vérifié en interne. Utilise cluster_id, mots_cles, exemples_tweets, sentiment_moyen, "
        "volume_messages, date_pic et nombre_communautes comme éléments d'analyse lorsqu'ils existent, "
        "sans en faire une conclusion automatique. "
        "Règle anti-répétition : compare mentalement les 3 sorties et varie les formulations selon les mots-clés "
        "et les tweets du cluster. Ne réutilise pas de phrases identiques ou quasi identiques d'une sortie à l'autre. "
        "Interdictions strictes dans les blocs SORTIE_LLM_X : ne jamais écrire 'rappeler le cadre, préciser les éléments vérifiés "
        "et éviter toute personnalisation du débat', ne jamais écrire 'clarification sobre, pas une riposte', "
        "ne jamais écrire 'fait interne validé, position officielle et validation juridique', "
        "ne jamais conclure automatiquement qu'il faut clarifier, répondre, rappeler le cadre ou éviter la personnalisation. "
        "Ensuite seulement, adopte le rôle d'un éditorialiste de crise : réponds à la question éditoriale ci-dessous "
        "en formulant un conseil argumenté, puis rédige une proposition de communiqué issue de ce conseil. "
        f"Question éditoriale posée au LLM final : {question_editoriale} "
        "Le conseil éditorial doit prendre une décision de posture : répondre, temporiser, contextualiser, démentir, "
        "reconnaître une inquiétude, ou combiner ces options. Il doit expliquer brièvement pourquoi. "
        "Le conseil éditorial doit monter la défense d'un cran lorsque les sorties LLM signalent des accusations structurées : "
        "identifier les sujets à défendre, les cadrages à refuser, les faits à opposer, et les points sur lesquels il ne faut "
        "pas rester dans une simple attente de vérification. "
        "Le communiqué final doit être directement lisible par un rédacteur en chef ou une direction de communication : "
        "pas de méta-commentaire, pas de formule du type 'nous allons déterminer la réponse appropriée', "
        "pas de formule faible du type 'nous reviendrons vers vous', 'nous regardons la meilleure réponse' ou "
        "'nous suivons la situation avec attention'. "
        "pas de mention de prompt, de LLM, de score, de cluster, de métrique interne ou de récit. "
        "Le communiqué doit répondre point par point aux sujets remontés dans les 3 sorties LLM : reconnaître ce qui mérite "
        "une vérification, mais défendre clairement ce qui peut l'être, rectifier les raccourcis et refuser les accusations "
        "présentées sans preuve. "
        "Le communiqué final doit obligatoirement reprendre les sujets nommés dans les 3 sorties LLM et rappeler l'historique "
        "minimal de la séquence lorsque les données le permettent : période, pic de visibilité, sujets attaqués, acteurs ou "
        "procédures évoqués. Il ne doit jamais rester générique. Pour chaque sujet principal, ajoute une phrase spécifique "
        "qui répond au cadrage observé. "
        "Si une sortie LLM relève d'un cadrage politique ou idéologique, comme une assignation à l'extrême droite, "
        "à l'extrême gauche ou à un camp partisan, le communiqué doit refuser ce procès d'intention en rappelant un principe "
        "républicain : les décisions publiques s'apprécient sur des règles, des critères vérifiables et des contrôles, "
        "pas sur des étiquettes politiques ou des culpabilités par proximité. "
        "Tu dois répondre en texte brut uniquement : aucun HTML, aucune balise, aucun markdown, aucun tableau. "
        "Respecte exactement ces marqueurs, car ils sont lus par l'interface :\n"
        "SORTIE_LLM_1 - RECIT CIBLE\n"
        "RECIT: [nom exact du récit choisi]\n"
        "MOTS_CLES_DOMINANTS: [mots-clés extraits ou résumés]\n"
        "RECIT_OBSERVE: [3 à 5 phrases décrivant le récit porté par les tweets, sans proposer de réponse]\n"
        "ELEMENTS_RECURRENTS:\n"
        "- [accusation, motif ou angle 1]\n"
        "- [accusation, motif ou angle 2]\n"
        "- [accusation, motif ou angle 3]\n"
        "SIGNAUX_POLARISATION: [vocabulaire accusatoire, ironique, politique, moral, financier, institutionnel, etc.]\n"
        "POINTS_A_VERIFIER:\n"
        "- [fait précis à vérifier]\n"
        "- [chiffre ou affirmation à confirmer]\n"
        "- [acteur, montant, procédure ou source à contrôler]\n\n"
        "SORTIE_LLM_2 - RECIT CIBLE\n"
        "RECIT: [nom exact du récit choisi]\n"
        "MOTS_CLES_DOMINANTS: [mots-clés extraits ou résumés]\n"
        "RECIT_OBSERVE: [3 à 5 phrases décrivant le récit porté par les tweets, sans proposer de réponse]\n"
        "ELEMENTS_RECURRENTS:\n"
        "- [accusation, motif ou angle 1]\n"
        "- [accusation, motif ou angle 2]\n"
        "- [accusation, motif ou angle 3]\n"
        "SIGNAUX_POLARISATION: [vocabulaire accusatoire, ironique, politique, moral, financier, institutionnel, etc.]\n"
        "POINTS_A_VERIFIER:\n"
        "- [fait précis à vérifier]\n"
        "- [chiffre ou affirmation à confirmer]\n"
        "- [acteur, montant, procédure ou source à contrôler]\n\n"
        "SORTIE_LLM_3 - RECIT CIBLE\n"
        "RECIT: [nom exact du récit choisi]\n"
        "MOTS_CLES_DOMINANTS: [mots-clés extraits ou résumés]\n"
        "RECIT_OBSERVE: [3 à 5 phrases décrivant le récit porté par les tweets, sans proposer de réponse]\n"
        "ELEMENTS_RECURRENTS:\n"
        "- [accusation, motif ou angle 1]\n"
        "- [accusation, motif ou angle 2]\n"
        "- [accusation, motif ou angle 3]\n"
        "SIGNAUX_POLARISATION: [vocabulaire accusatoire, ironique, politique, moral, financier, institutionnel, etc.]\n"
        "POINTS_A_VERIFIER:\n"
        "- [fait précis à vérifier]\n"
        "- [chiffre ou affirmation à confirmer]\n"
        "- [acteur, montant, procédure ou source à contrôler]\n\n"
        "CONSEIL_EDITORIAL\n"
        "POSTURE_RECOMMANDEE: [répondre / temporiser / contextualiser / démentir / reconnaître une inquiétude / combinaison]\n"
        "NIVEAU_FERMETE: [faible / moyen / fort]\n"
        "ARGUMENT: [raison éditoriale courte]\n"
        "POINTS_A_DEFENDRE: [sujets des sorties LLM à défendre ou rectifier explicitement]\n"
        "CADRAGES_A_REFUSER: [accusations, raccourcis ou généralisations à ne pas laisser s'installer]\n"
        "POINTS_A_TRAITER: [points qui doivent apparaître dans le communiqué]\n"
        "TERMES_A_EVITER: [formulations ou pièges à éviter]\n\n"
        "BROUILLON_FINAL_CONSOLIDE\n"
        "[communiqué final public, avec historique minimal et reprise explicite des 3 sujets principaux, directement publiable après validation humaine]\n\n"
        "POINTS_VALIDATION_HUMAINE\n"
        "- [point 1]\n"
        "- [point 2]\n\n"
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
        volume = recit.get("volume", "n/a")
        mots_cles = ", ".join(str(mot) for mot in recit.get("mots_cles", [])[:6]) or recit_nom
        observation = nettoyer_sortie_llm(recit.get("observation", ""))
        if not observation:
            observation = (
                "Les tweets regroupés dans ce cluster convergent autour d'un angle critique récurrent, "
                "avec une formulation souvent accusatoire ou interrogative."
            )
        lignes.append(
            f"SORTIE_LLM_{index} - RECIT CIBLE\n"
            f"RECIT: {recit_nom}\n"
            f"MOTS_CLES_DOMINANTS: {mots_cles}\n"
            "RECIT_OBSERVE: "
            f"Le cluster rassemble {volume} messages autour d'un cadrage associé à {recit_nom}. "
            f"L'exemple représentatif indique le type d'accusation ou d'interrogation porté par les tweets : {observation} "
            "La tonalité disponible signale une charge négative mesurée, sans permettre à elle seule de conclure sur la véracité des affirmations.\n"
            "ELEMENTS_RECURRENTS:\n"
            f"- Association répétée entre {recit_nom} et un grief public identifiable.\n"
            "- Usage d'exemples ou de noms propres pour rendre le cadrage plus concret.\n"
            "- Généralisation possible à partir de cas isolés ou de formulations virales.\n"
            "SIGNAUX_POLARISATION: "
            f"La part négative estimée à {pct_negative}% suggère un registre critique. "
            "Le vocabulaire doit être relu comme signal de perception, pas comme preuve factuelle.\n"
            "POINTS_A_VERIFIER:\n"
            f"- Affirmations précises associées au récit « {recit_nom} ».\n"
            "- Chiffres, dates, montants ou procédures mentionnés dans les tweets du cluster.\n"
            "- Acteurs cités, sources primaires disponibles et contexte de publication."
        )

    if not lignes:
        return (
            "Aucun récit exploitable n'est disponible pour générer les 3 réponses prioritaires."
        )

    sorties_secours = extraire_sorties_llm("\n\n".join(lignes))
    conseil_editorial = construire_conseil_editorial_depuis_sorties(sorties_secours, payload)
    sujets = sujets_publics_depuis_sorties(sorties_secours, 3)
    historique = phrase_historique_public(payload)
    reponses_sujets = " ".join(phrase_defense_sujet(sujet) for sujet in sujets)
    brouillon_final = (
        "Les accusations relayées appellent une réponse claire. "
        + historique
        + " "
        "Nous contestons les raccourcis qui transforment des soupçons ou des exemples isolés en conclusions générales. "
        + reponses_sujets
        + " Les faits doivent être établis à partir de documents, de procédures et de données vérifiables, pas à partir "
        "d'insinuations. Notre position est ferme : les règles, les critères d'attribution et les contrôles existants "
        "doivent être regardés précisément avant toute mise en cause. "
        "Les points exacts cités publiquement seront traités un par un ; ce qui est vérifié sera expliqué, ce qui ne l'est pas "
        "ne sera pas présenté comme un fait. Nous répondrons sur le fond, sans attaque personnelle et sans laisser s'installer "
        "des accusations générales non démontrées."
    )

    return (
        "\n\n".join(lignes)
        + "\n\nCONSEIL_EDITORIAL\n"
        + conseil_editorial
        + "\n\nBROUILLON_FINAL_CONSOLIDE\n"
        + brouillon_final
        + "\n\nPOINTS_VALIDATION_HUMAINE\n"
        "- Faits précis cités dans les tweets.\n"
        "- Chiffres, dates, montants et procédures.\n"
        "- Validation des sources internes mobilisables."
    )


def _lire_secret_ou_config(nom_cle: str) -> str | None:
    try:
        if nom_cle in st.secrets:
            return st.secrets[nom_cle]
    except Exception:
        pass
    return os.getenv(nom_cle) or config(nom_cle, default=None)


def cle_gemini() -> str | None:
    return _lire_secret_ou_config("GEMINI_API_KEY")


def _nettoyer_cle_api(api_key: str | None) -> str:
    if api_key is None:
        return ""
    return str(api_key).strip()


def _cle_api_valide(api_key: str) -> bool:
    return bool(api_key) and not bool(re.search(r"\s", api_key))


def _fournisseur_llm_actif(fournisseur: str | None = None) -> str:
    fournisseur_actif = (fournisseur or os.getenv("LLM_PROVIDER") or FOURNISSEUR_LLM_DEFAUT).strip()
    return fournisseur_actif if fournisseur_actif in FOURNISSEURS_LLM else FOURNISSEUR_LLM_DEFAUT


def _source_cle_llm(fournisseur: str) -> tuple[str, str | None]:
    nom_cle = FOURNISSEURS_LLM[fournisseur]["env"]
    try:
        if nom_cle in st.secrets:
            return "Streamlit secrets", st.secrets[nom_cle]
    except Exception:
        pass

    cle_env = os.getenv(nom_cle)
    if cle_env:
        return "Variable d'environnement", cle_env

    cle_config = config(nom_cle, default=None)
    if cle_config:
        return ".env / python-decouple", cle_config

    return "Aucune clé détectée", None


def _modele_llm_actif(fournisseur: str, modele: str | None = None) -> str:
    modeles = FOURNISSEURS_LLM[fournisseur]["modeles"]
    variable_modele = os.getenv("LLM_MODEL") or os.getenv(f"{FOURNISSEURS_LLM[fournisseur]['env'][:-8]}MODEL")
    modele_actif = (modele or variable_modele or modeles[0]).strip()
    if modele_actif in MODELES_GEMINI_OBSOLETES:
        return MODELE_GEMINI_DEFAUT
    return modele_actif


def _modele_gemini_actif(modele: str | None = None) -> str:
    modele_actif = (modele or os.getenv("GEMINI_MODEL") or _modele_llm_actif("Google Gemini")).strip()
    if modele_actif in MODELES_GEMINI_OBSOLETES:
        return MODELE_GEMINI_DEFAUT
    return modele_actif


def _modeles_llm_a_tester(fournisseur: str, modele: str | None = None) -> list[str]:
    premier = _modele_llm_actif(fournisseur, modele)
    modeles = [premier]
    for modele_repli in FOURNISSEURS_LLM[fournisseur]["modeles"]:
        if fournisseur == "Google Gemini":
            modele_repli = _modele_gemini_actif(modele_repli)
        if modele_repli not in modeles:
            modeles.append(modele_repli)
    return modeles


def _modeles_gemini_a_tester(modele: str | None = None) -> list[str]:
    return _modeles_llm_a_tester("Google Gemini", modele)


def _erreur_llm_transitoire(statut: str) -> bool:
    motifs = ["HTTP 503", "HTTP 429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "rate limit", "overloaded"]
    return any(motif.lower() in statut.lower() for motif in motifs)


def _erreur_gemini_transitoire(statut: str) -> bool:
    return _erreur_llm_transitoire(statut)


def _requete_json(
    url: str,
    corps: dict,
    headers: dict,
    fournisseur: str,
    modele: str,
) -> tuple[dict | None, str]:
    requete = urllib.request.Request(
        url,
        data=json.dumps(corps).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(requete, timeout=30) as reponse:
            return json.loads(reponse.read().decode("utf-8")), ""
    except urllib.error.HTTPError as erreur:
        detail = erreur.read().decode("utf-8", errors="ignore")
        return None, f"Erreur {fournisseur} HTTP {erreur.code} avec {modele} : {detail[:500]}"
    except urllib.error.URLError as erreur:
        return None, f"{fournisseur} inaccessible avec {modele} : {erreur.reason}"
    except http.client.InvalidURL as erreur:
        return None, f"URL {fournisseur} invalide : vérifie que la clé API ne contient aucun texte parasite. Détail : {erreur}"
    except TimeoutError:
        return None, f"{fournisseur} inaccessible avec {modele} : délai dépassé."
    except ValueError as erreur:
        return None, f"Appel {fournisseur} invalide avec {modele} : {erreur}"


def _appeler_gemini_modele(
    prompt: str,
    api_key: str,
    modele: str,
    max_tokens: int = 2200,
) -> tuple[str, str]:
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
            "maxOutputTokens": max_tokens,
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
        if erreur.code == 404:
            return (
                "",
                f"Erreur Gemini HTTP 404 : modèle '{modele}' indisponible pour generateContent. "
                f"Essaie '{MODELE_GEMINI_DEFAUT}' ou 'gemini-flash-latest'. Détail : {detail[:500]}",
            )
        return "", f"Erreur Gemini HTTP {erreur.code} : {detail[:500]}"
    except urllib.error.URLError as erreur:
        return "", f"Gemini inaccessible : {erreur.reason}"
    except http.client.InvalidURL as erreur:
        return "", f"URL Gemini invalide : vérifie que la clé API ne contient aucun texte parasite. Détail : {erreur}"
    except ValueError as erreur:
        return "", f"Appel Gemini invalide : {erreur}"
    except TimeoutError:
        return "", "Gemini inaccessible : délai dépassé."

    candidats = resultat.get("candidates", [])
    if not candidats:
        return "", f"Gemini n'a renvoyé aucun candidat exploitable : {resultat}"

    morceaux = candidats[0].get("content", {}).get("parts", [])
    texte = "\n".join(part.get("text", "") for part in morceaux if part.get("text")).strip()
    if not texte:
        return "", f"Réponse Gemini vide : {resultat}"
    return texte, f"Réponse générée par Gemini avec {modele}."


def _appeler_openai_modele(
    prompt: str,
    api_key: str,
    modele: str,
    max_tokens: int = 2200,
) -> tuple[str, str]:
    resultat, erreur = _requete_json(
        "https://api.openai.com/v1/responses",
        {
            "model": modele,
            "input": prompt,
            "temperature": 0.35,
            "max_output_tokens": max_tokens,
        },
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        "OpenAI",
        modele,
    )
    if erreur:
        return "", erreur

    texte = (resultat or {}).get("output_text", "")
    if not texte:
        morceaux = []
        for sortie in (resultat or {}).get("output", []):
            for contenu in sortie.get("content", []):
                if contenu.get("type") in {"output_text", "text"} and contenu.get("text"):
                    morceaux.append(contenu["text"])
        texte = "\n".join(morceaux).strip()
    if not texte:
        return "", f"Réponse OpenAI vide avec {modele} : {resultat}"
    return texte, f"Réponse générée par OpenAI avec {modele}."


def _appeler_anthropic_modele(
    prompt: str,
    api_key: str,
    modele: str,
    max_tokens: int = 2200,
) -> tuple[str, str]:
    resultat, erreur = _requete_json(
        "https://api.anthropic.com/v1/messages",
        {
            "model": modele,
            "max_tokens": max_tokens,
            "temperature": 0.35,
            "messages": [{"role": "user", "content": prompt}],
        },
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        "Anthropic Claude",
        modele,
    )
    if erreur:
        return "", erreur

    morceaux = [
        contenu.get("text", "")
        for contenu in (resultat or {}).get("content", [])
        if contenu.get("type") == "text" and contenu.get("text")
    ]
    texte = "\n".join(morceaux).strip()
    if not texte:
        return "", f"Réponse Anthropic vide avec {modele} : {resultat}"
    return texte, f"Réponse générée par Anthropic Claude avec {modele}."


def _appeler_mistral_modele(
    prompt: str,
    api_key: str,
    modele: str,
    max_tokens: int = 2200,
) -> tuple[str, str]:
    resultat, erreur = _requete_json(
        "https://api.mistral.ai/v1/chat/completions",
        {
            "model": modele,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.35,
            "max_tokens": max_tokens,
        },
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        "Mistral AI",
        modele,
    )
    if erreur:
        return "", erreur

    choix = (resultat or {}).get("choices", [])
    texte = choix[0].get("message", {}).get("content", "").strip() if choix else ""
    if not texte:
        return "", f"Réponse Mistral vide avec {modele} : {resultat}"
    return texte, f"Réponse générée par Mistral AI avec {modele}."


def _appeler_llm_modele(
    fournisseur: str,
    prompt: str,
    api_key: str,
    modele: str,
    max_tokens: int = 2200,
) -> tuple[str, str]:
    if fournisseur == "Google Gemini":
        return _appeler_gemini_modele(prompt, api_key, modele, max_tokens)
    if fournisseur == "OpenAI":
        return _appeler_openai_modele(prompt, api_key, modele, max_tokens)
    if fournisseur == "Anthropic Claude":
        return _appeler_anthropic_modele(prompt, api_key, modele, max_tokens)
    if fournisseur == "Mistral AI":
        return _appeler_mistral_modele(prompt, api_key, modele, max_tokens)
    return "", f"Fournisseur LLM non supporté : {fournisseur}"


def appeler_llm(
    prompt: str,
    fournisseur: str | None = None,
    api_key: str | None = None,
    modele: str | None = None,
    max_tokens: int = 2200,
) -> tuple[str, str]:
    fournisseur = _fournisseur_llm_actif(fournisseur)
    api_key = _nettoyer_cle_api(api_key or _source_cle_llm(fournisseur)[1])
    if not api_key:
        nom_cle = FOURNISSEURS_LLM[fournisseur]["env"]
        return "", f"Clé {fournisseur} absente : définis {nom_cle} dans .env, Streamlit secrets ou ton shell."
    if not _cle_api_valide(api_key):
        return "", f"Clé {fournisseur} invalide : elle contient des espaces ou des retours ligne. Colle uniquement la clé API."

    statuts = []
    for modele_a_tester in _modeles_llm_a_tester(fournisseur, modele):
        reponse, statut = _appeler_llm_modele(
            fournisseur,
            prompt,
            api_key=api_key,
            modele=modele_a_tester,
            max_tokens=max_tokens,
        )
        if reponse:
            if statuts:
                return reponse, f"{statut} Repli automatique après indisponibilité temporaire."
            return reponse, statut

        statuts.append(f"{modele_a_tester} -> {statut}")
        if not _erreur_llm_transitoire(statut):
            break

    return "", f"Tous les essais {fournisseur} ont échoué : " + " | ".join(statuts)


def appeler_gemini(
    prompt: str,
    api_key: str | None = None,
    modele: str | None = None,
    max_tokens: int = 2200,
) -> tuple[str, str]:
    return appeler_llm(
        prompt,
        fournisseur="Google Gemini",
        api_key=api_key,
        modele=modele,
        max_tokens=max_tokens,
    )


def nettoyer_sortie_llm(texte: str) -> str:
    texte = str(texte or "")
    texte = re.sub(r"```[a-zA-Z]*", "", texte)
    texte = texte.replace("```", "")
    texte = re.sub(r"</?div[^>]*>", "", texte, flags=re.IGNORECASE)
    texte = re.sub(r"<[^>]+>", "", texte)
    texte = re.sub(r"^\s{0,3}#{1,6}\s*", "", texte, flags=re.MULTILINE)
    texte = re.sub(r"\*\*(.*?)\*\*", r"\1", texte)
    texte = re.sub(r"__(.*?)__", r"\1", texte)
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    return texte.strip()


def extraire_brouillon_consolide(texte_llm: str) -> str:
    texte_llm = nettoyer_sortie_llm(texte_llm)
    marqueurs = ["BROUILLON_FINAL_CONSOLIDE", "Brouillon final consolidé"]
    marqueur = next((item for item in marqueurs if item in texte_llm), None)
    if not marqueur:
        return ""

    apres_marqueur = texte_llm.split(marqueur, 1)[1].strip()
    for separateur in ["POINTS_VALIDATION_HUMAINE", "Points de validation humaine", "Points de validation"]:
        if separateur in apres_marqueur:
            return apres_marqueur.split(separateur, 1)[0].strip()
    apres_marqueur = re.split(r"\n\s*SORTIE_LLM_[123]\b", apres_marqueur, maxsplit=1)[0].strip()
    return apres_marqueur


def extraire_conseil_editorial(texte_llm: str) -> str:
    texte_llm = nettoyer_sortie_llm(texte_llm)
    marqueurs = ["CONSEIL_EDITORIAL", "Conseil éditorial", "Conseil editorial"]
    marqueur = next((item for item in marqueurs if item in texte_llm), None)
    if not marqueur:
        return ""

    apres_marqueur = texte_llm.split(marqueur, 1)[1].strip()
    for separateur in ["BROUILLON_FINAL_CONSOLIDE", "Brouillon final consolidé", "POINTS_VALIDATION_HUMAINE"]:
        if separateur in apres_marqueur:
            return apres_marqueur.split(separateur, 1)[0].strip()
    return apres_marqueur


def _texte_reponse_depuis_sortie(sortie: dict) -> str:
    texte = nettoyer_sortie_llm(sortie.get("texte", ""))
    correspondance = re.search(
        r"Réponse proposée\s*:\s*(.*?)(?:\n\s*Point à valider\s*:|\Z)",
        texte,
        re.DOTALL | re.IGNORECASE,
    )
    return nettoyer_sortie_llm(correspondance.group(1) if correspondance else texte)


def _nom_recit_public(recit: str) -> str:
    recit = nettoyer_sortie_llm(recit)
    recit = re.sub(r"\s*[·-]\s*\d[\d\s,.]*\s*messages?.*$", "", recit, flags=re.IGNORECASE)
    return recit.strip(" .;")


def sujets_publics_depuis_sorties(sorties: list[dict], limite: int = 3) -> list[str]:
    sujets = []
    for sortie in sorties:
        sujet = _nom_recit_public(sortie.get("recit", ""))
        if sujet and sujet not in sujets:
            sujets.append(sujet)
    return sujets[:limite]


def phrase_historique_public(payload: dict) -> str:
    propagation = payload.get("propagation", {}) if isinstance(payload.get("propagation"), dict) else {}
    coordination = payload.get("coordination", {}).get("resume", {}) if isinstance(payload.get("coordination"), dict) else {}
    pic = propagation.get("pic", {}) if isinstance(propagation.get("pic"), dict) else {}
    date_pic = pic.get("date")
    communautes = coordination.get("communautes_retenues")
    morceaux = []
    if date_pic:
        morceaux.append(f"Cette séquence a connu un pic de visibilité le {date_pic}")
    if communautes:
        morceaux.append(f"elle s'est diffusée dans {communautes} espaces de discussion identifiés")
    if not morceaux:
        return "Cette séquence publique a fait émerger plusieurs accusations et interrogations distinctes."
    return ", et ".join(morceaux) + "."


def sujet_politique_ideologique(sujet: str) -> bool:
    sujet_normalise = nettoyer_sortie_llm(sujet).lower()
    marqueurs = [
        "extrême droite",
        "extreme droite",
        "extrême gauche",
        "extreme gauche",
        "droite",
        "gauche",
        "lfi",
        "rn",
        "front national",
        "partisan",
        "politique",
        "idéologique",
        "ideologique",
    ]
    return any(marqueur in sujet_normalise for marqueur in marqueurs)


def phrase_defense_sujet(sujet: str) -> str:
    sujet = sujet.strip(" .;")
    if not sujet:
        return ""
    if sujet_politique_ideologique(sujet):
        return (
            "Sur les tentatives d'assignation politique, notre réponse est simple : la République ne fonctionne pas "
            "par procès d'intention. Elle fonctionne par des règles publiques, des critères vérifiables et des contrôles."
        )
    return (
        f"Sur {sujet}, nous contestons les raccourcis et renvoyons aux faits vérifiables, aux procédures et aux éléments documentés."
    )


def _mots_recit(recit: str) -> set[str]:
    return {
        mot
        for mot in re.findall(r"[a-zA-ZÀ-ÿ0-9]{3,}", nettoyer_sortie_llm(recit).lower())
        if mot not in {"messages", "neg", "nég", "recit", "récit"}
    }


def _recit_source_pour_sortie(sortie: dict, payload: dict) -> dict:
    recits = payload.get("recits_narration_6_observations", [])
    if not recits:
        return {}

    cible = _mots_recit(sortie.get("recit", ""))
    if not cible:
        index = int(sortie.get("index", 1) or 1) - 1
        return recits[index] if 0 <= index < len(recits) else {}

    def score(recit: dict) -> int:
        mots = _mots_recit(" ".join([str(recit.get("nom", "")), " ".join(recit.get("mots_cles", []))]))
        return len(cible & mots)

    return max(recits, key=score, default={})


def exemples_tweets_pour_sortie(sortie: dict, payload: dict) -> list[str]:
    recit = _recit_source_pour_sortie(sortie, payload)
    if not recit:
        return []

    exemples = []
    rag = payload.get("rag", {}) if isinstance(payload.get("rag"), dict) else {}
    exemples_rag = rag.get("exemples_par_recit", {})
    for item in exemples_rag.get(str(recit.get("id")), []):
        message = nettoyer_sortie_llm(item.get("message", ""))
        if message:
            exemples.append(message)

    if len(exemples) < 10:
        for message in payload.get("exemples_dataset_par_recit", {}).get(str(recit.get("id")), []):
            message = nettoyer_sortie_llm(message)
            if message:
                exemples.append(message)

    if len(exemples) < 10 and recit.get("observation"):
        exemples.append(nettoyer_sortie_llm(recit.get("observation")))

    uniques = []
    for exemple in exemples:
        exemple = exemple.strip()
        if exemple and exemple not in uniques:
            uniques.append(exemple)
    return uniques[:10]


def construire_brouillon_depuis_sorties(sorties: list[dict], payload: dict) -> str:
    if not sorties:
        return ""

    axes_publics = sujets_publics_depuis_sorties(sorties, 3)
    historique = phrase_historique_public(payload)

    points = []
    for axe in axes_publics[:3]:
        nom = axe.split("·", 1)[0].strip(" .;")
        if not nom:
            continue
        points.append(phrase_defense_sujet(nom))

    if not points:
        points.append("Sur les interrogations exprimées, nous contestons les raccourcis et renvoyons aux faits vérifiables.")

    return (
        "Nous avons pris connaissance des accusations et des interrogations relayées ces derniers jours. "
        + historique
        + " "
        "Notre position est claire : le débat public mérite des faits établis, pas des insinuations ni des raccourcis. "
        + " ".join(points)
        + " Les affirmations qui circulent seront confrontées aux documents, aux procédures et aux données vérifiables. "
        "Nous refusons les mises en cause personnelles et les généralisations abusives, tout en reconnaissant la légitimité "
        "des questions posées lorsqu'elles portent sur l'usage de ressources publiques ou l'équité d'accès aux dispositifs. "
        "Les éléments confirmés seront publiés de manière lisible ; les points non établis ne seront pas présentés comme des faits."
    )


def construire_conseil_editorial_depuis_sorties(sorties: list[dict], payload: dict) -> str:
    axes = [_nom_recit_public(sortie.get("recit", "")) for sortie in sorties if sortie.get("recit")]
    axes = [axe for axe in axes if axe]
    axes_texte = ", ".join(axes[:3]) if axes else "les griefs principaux détectés"
    return (
        "POSTURE_RECOMMANDEE: répondre par une clarification ferme et factuelle.\n"
        "NIVEAU_FERMETE: fort sur les faits, mesuré sur le ton.\n"
        f"ARGUMENT: les signaux observés sur {axes_texte} portent des accusations suffisamment structurées pour qu'une absence "
        "de réponse laisse le cadrage polémique s'installer. La réponse doit donc poser une position claire sans nourrir "
        "l'affrontement.\n"
        f"POINTS_A_DEFENDRE: les sujets associés à {axes_texte}, les procédures vérifiables, l'équité de traitement et "
        "la distinction entre faits établis et soupçons relayés.\n"
        "CADRAGES_A_REFUSER: insinuations présentées comme des preuves, généralisations à partir de cas isolés, "
        "mise en cause personnelle et accusation de fonctionnement opaque sans élément contrôlable.\n"
        "POINTS_A_TRAITER: faits vérifiables, procédures, équité d'accès, distinction entre accusation et élément établi.\n"
        "TERMES_A_EVITER: attaques personnelles, ironie, minimisation, promesse vague de revenir ultérieurement."
    )


def construire_analyse_situation(sorties: list[dict], payload: dict) -> str:
    if not sorties:
        return ""

    propagation = payload.get("propagation", {})
    coordination = payload.get("coordination", {}).get("resume", {})
    pic = propagation.get("pic", {})
    communautes = coordination.get("communautes_retenues", "n/a")
    axes = [nettoyer_sortie_llm(sortie.get("recit", "")) for sortie in sorties if sortie.get("recit")]
    observations = [_texte_reponse_depuis_sortie(sortie) for sortie in sorties]
    observations = [observation for observation in observations if observation]

    phrases = ["Les analyses font apparaître plusieurs récits concurrents qui structurent la perception publique du sujet."]
    if axes:
        phrases.append("Les trois clusters les plus sensibles observés concernent : " + " ; ".join(axes[:3]) + ".")
    if observations:
        phrases.append("Lecture des signaux : " + " ".join(observations[:3]))
    if pic or communautes != "n/a":
        phrases.append(
            f"Le pic observé le {pic.get('date', 'n/a')} et la structuration en {communautes} communautés décrivent "
            "un épisode de visibilité segmenté, dont l'interprétation doit rester prudente sans vérification interne."
        )
    phrases.append("Les éléments listés doivent être considérés comme des observations issues des tweets, pas comme des faits établis.")
    return " ".join(phrases)


def extraire_sorties_llm(texte_llm: str) -> list[dict]:
    if not texte_llm:
        return []

    section = nettoyer_sortie_llm(texte_llm)
    sorties_marquees = []
    for correspondance in re.finditer(
        r"SORTIE_LLM_(?P<index>[123])(?:\s*-\s*RECIT CIBLE)?\s+RECIT\s*:\s*(?P<recit>.*?)(?=\n\s*MOTS_CLES_DOMINANTS\s*:)"
        r"\n\s*(?P<texte>MOTS_CLES_DOMINANTS\s*:.*?)(?=\n\s*SORTIE_LLM_[123](?:\s*-\s*RECIT CIBLE)?|\n\s*BROUILLON_FINAL_CONSOLIDE|\Z)",
        section,
        re.DOTALL | re.IGNORECASE,
    ):
        sorties_marquees.append(
            {
                "index": correspondance.group("index"),
                "recit": nettoyer_sortie_llm(correspondance.group("recit")),
                "texte": nettoyer_sortie_llm(correspondance.group("texte")),
            }
        )
    if sorties_marquees:
        return sorties_marquees[:3]

    for correspondance in re.finditer(
        r"SORTIE_LLM_(?P<index>[123])\s+RECIT\s*:\s*(?P<recit>.*?)\s+REPONSE\s*:\s*(?P<reponse>.*?)\s+VALIDATION\s*:\s*(?P<validation>.*?)(?=\s+SORTIE_LLM_[123]|\s+BROUILLON_FINAL_CONSOLIDE|\Z)",
        section,
        re.DOTALL | re.IGNORECASE,
    ):
        reponse = nettoyer_sortie_llm(correspondance.group("reponse"))
        validation = nettoyer_sortie_llm(correspondance.group("validation"))
        sorties_marquees.append(
            {
                "index": correspondance.group("index"),
                "recit": nettoyer_sortie_llm(correspondance.group("recit")),
                "texte": f"Réponse proposée : {reponse}\nPoint à valider : {validation}",
            }
        )
    if sorties_marquees:
        return sorties_marquees[:3]

    if "Sorties intermédiaires LLM" in section:
        section = section.split("Sorties intermédiaires LLM", 1)[1]
    if "Brouillon final consolidé" in section:
        section = section.split("Brouillon final consolidé", 1)[0]
    if "BROUILLON_FINAL_CONSOLIDE" in section:
        section = section.split("BROUILLON_FINAL_CONSOLIDE", 1)[0]

    blocs = re.split(r"\n\s*(?=\d+[\).\s-]+(?:Récit ciblé|RECIT|Récit)\s*:?)", section.strip(), flags=re.IGNORECASE)
    sorties = []
    for bloc in blocs:
        bloc = nettoyer_sortie_llm(bloc)
        if not bloc:
            continue
        correspondance = re.match(
            r"(?P<index>\d+)[\).\s-]+(?:Récit ciblé|RECIT|Récit)\s*:?\s*(?P<recit>[^\n]+)\n?(?P<texte>.*)",
            bloc,
            re.DOTALL | re.IGNORECASE,
        )
        if not correspondance:
            continue

        texte = nettoyer_sortie_llm(correspondance.group("texte"))
        texte = re.sub(r"\n\s+Réponse proposée\s*:", "\nRéponse proposée :", texte)
        texte = re.sub(r"\n\s+Point à valider\s*:", "\nPoint à valider :", texte)
        sorties.append(
            {
                "index": correspondance.group("index"),
                "recit": nettoyer_sortie_llm(correspondance.group("recit")),
                "texte": texte,
            }
        )
    return sorties[:3]


def sorties_llm_secours(payload: dict) -> list[dict]:
    return extraire_sorties_llm(generer_reponse_degonflage(payload))


def injecter_style_sorties_llm() -> None:
    st.markdown(
        """
        <style>
            .px8-llm-card {
                background: #ffffff;
                border: 1px solid #dbe4ef;
                border-left: 7px solid #7c6cff;
                border-radius: 8px;
                box-shadow: 0 18px 34px rgba(15, 23, 42, 0.08);
                margin: 14px 0 18px;
                padding: 22px 28px;
            }
            .px8-llm-card.final {
                border-left-color: #119c7d;
            }
            .px8-llm-card.toolbox {
                border-left-color: #111827;
            }
            .px8-llm-title {
                color: #7c6cff;
                font-family: "HK Grotesk", Inter, system-ui, sans-serif;
                font-size: 0.98rem;
                font-weight: 850;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                margin-bottom: 14px;
            }
            .px8-llm-card.final .px8-llm-title {
                color: #119c7d;
            }
            .px8-llm-card.toolbox .px8-llm-title {
                color: #111827;
            }
            .px8-llm-meta {
                color: #66758a;
                font-size: 1.04rem;
                font-weight: 760;
                margin-bottom: 16px;
            }
            .px8-llm-body {
                color: #172033;
                font-size: 1.02rem;
                font-weight: 500;
                line-height: 1.55;
                white-space: pre-wrap;
            }
            .px8-llm-label {
                font-weight: 850;
                color: #111827;
            }
            .px8-llm-examples {
                display: block;
                width: 100%;
                box-sizing: border-box;
                margin: 10px 0 8px;
                padding: 10px 12px;
                border-left: 3px solid #d8d1ff;
                border-radius: 8px;
                background: #f7f8fb;
                color: #66758a;
                font-size: .88rem;
                line-height: 1.42;
                white-space: normal !important;
                overflow: visible !important;
                height: auto !important;
                max-height: none !important;
            }
            .px8-llm-examples-title {
                color: #7c6cff;
                font-family: "HK Grotesk", Inter, system-ui, sans-serif;
                font-size: .78rem;
                font-weight: 850;
                letter-spacing: .04em;
                text-transform: uppercase;
                margin-bottom: 5px;
            }
            .px8-llm-example {
                display: block;
                width: 100%;
                box-sizing: border-box;
                margin: 7px 0;
                color: #4f5f72;
                white-space: normal !important;
                overflow: visible !important;
                overflow-wrap: break-word;
                word-break: break-word;
                hyphens: auto;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def formater_libelles_llm(texte: str) -> str:
    lignes = []
    for ligne in str(texte or "Contenu non disponible.").splitlines():
        correspondance = re.match(r"^(\s*)([A-ZÀ-Ÿ0-9_ /'’.-]{2,80})\s*:\s*(.*)$", ligne)
        if correspondance:
            indentation, libelle, contenu = correspondance.groups()
            lignes.append(
                f"{escape(indentation)}<span class=\"px8-llm-label\">{escape(libelle.strip())} :</span> {escape(contenu)}"
            )
        else:
            lignes.append(escape(ligne))
    return "\n".join(lignes)


def afficher_carte_sortie_llm(titre: str, meta: str, texte: str, final: bool = False) -> None:
    classe_finale = " final" if final else ""
    corps = formater_libelles_llm(texte)
    st.markdown(
        f"""
        <div class="px8-llm-card{classe_finale}">
            <div class="px8-llm-title">{escape(titre)}</div>
            <div class="px8-llm-meta">{escape(meta)}</div>
            <div class="px8-llm-body">{corps}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def afficher_exemples_tweets_llm(exemples: list[str], cle: str) -> None:
    if not exemples:
        return
    nombre_exemples = len(exemples)
    lignes = "".join(
        f'<div class="px8-llm-example"><strong>{index}.</strong> {escape(exemple)}</div>'
        for index, exemple in enumerate(exemples, start=1)
    )
    st.markdown(
        f"""
        <div class="px8-llm-examples">
            <div class="px8-llm-examples-title">{nombre_exemples} exemples de tweets utilisés pour la classification</div>
            {lignes}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _source_cle_gemini() -> tuple[str, str | None]:
    return _source_cle_llm("Google Gemini")


def _masquer_cle(api_key: str | None) -> str:
    if not api_key:
        return "Non configurée"
    if len(api_key) <= 10:
        return "••••"
    return f"{api_key[:4]}••••{api_key[-4:]}"


def _afficher_boite_outils_api() -> None:
    injecter_style_sorties_llm()
    fournisseur_defaut = _fournisseur_llm_actif()

    st.markdown(
        """
        <div class="px8-llm-card toolbox">
            <div class="px8-llm-title">Boîte à outils API</div>
            <div class="px8-llm-meta">Tester les clés LLM utilisées par la proposition haute</div>
            <div class="px8-llm-body">
                Vérifie les 4 fournisseurs principaux, le modèle appelé et la capacité à générer une réponse courte.
                La clé n'est jamais affichée en clair.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    colonnes_statut = st.columns(4)
    for colonne, fournisseur in zip(colonnes_statut, FOURNISSEURS_LLM):
        source, cle = _source_cle_llm(fournisseur)
        with colonne:
            st.metric(fournisseur, "OK" if cle else "Absente")
            st.caption(f"{source} · {_masquer_cle(cle)}")

    col_fournisseur, col_modele = st.columns([1, 1])
    with col_fournisseur:
        fournisseur_test = st.selectbox(
            "Fournisseur de test",
            list(FOURNISSEURS_LLM.keys()),
            index=list(FOURNISSEURS_LLM.keys()).index(fournisseur_defaut),
            key="llm_toolbox_provider",
        )
    with col_modele:
        modeles_disponibles = FOURNISSEURS_LLM[fournisseur_test]["modeles"]
        modele_test = st.selectbox(
            "Modèle de test",
            modeles_disponibles,
            key=f"llm_toolbox_model_{fournisseur_test}",
        )

    cle_temporaire = st.text_input(
        "Clé API temporaire",
        type="password",
        placeholder="Optionnel : colle une clé ici pour tester sans modifier .env",
        key=f"llm_toolbox_key_{fournisseur_test}",
    )
    prompt_test = st.text_area(
        "Prompt de test",
        value="Réponds uniquement : Connexion LLM opérationnelle pour PX8.",
        height=90,
        key="llm_toolbox_prompt",
    )

    col_test, col_infos = st.columns([0.22, 0.78])
    with col_test:
        tester = st.button("Tester le LLM", type="primary", key="llm_toolbox_test")
    with col_infos:
        nom_cle = FOURNISSEURS_LLM[fournisseur_test]["env"]
        st.caption(
            f"Priorité de clé : champ temporaire, puis Streamlit secrets, variable d'environnement, fichier .env. "
            f"Pour ce fournisseur : {nom_cle}."
        )

    if tester:
        _, cle_detectee = _source_cle_llm(fournisseur_test)
        cle_utilisee = _nettoyer_cle_api(cle_temporaire or cle_detectee)
        if not cle_utilisee:
            st.error("Aucune clé disponible pour lancer le test.")
            return
        if not _cle_api_valide(cle_utilisee):
            st.error("La clé testée contient des espaces ou du texte parasite. Colle uniquement la clé API.")
            return
        with st.spinner(f"Test {fournisseur_test} en cours..."):
            reponse, statut = appeler_llm(
                prompt_test,
                fournisseur=fournisseur_test,
                api_key=cle_utilisee,
                modele=modele_test,
                max_tokens=120,
            )
        if reponse:
            st.success(statut)
            st.code(reponse, language="text")
        else:
            st.error(statut)


def _afficher_editeur_prompt_final() -> None:
    injecter_style_sorties_llm()
    with st.expander("Réglage avancé - question posée au LLM final", expanded=False):
        st.caption(
            "Cette zone n'est pas un contenu éditorial. Elle sert uniquement à ajuster la question posée au LLM final."
        )
        st.text_area(
            "Question éditoriale",
            value=consigne_reponse_finale(),
            height=110,
            key="prompt_reponse_finale_llm",
        )


def _cle_cache_reponse_llm(prompt: str) -> str:
    fournisseur = _fournisseur_llm_actif()
    modele = _modele_llm_actif(fournisseur)
    empreinte = hashlib.sha256(f"{fournisseur}|{modele}|{prompt}".encode("utf-8")).hexdigest()
    return f"proposition_finale_llm_{empreinte}"


def _obtenir_reponse_llm(prompt: str, payload: dict, forcer_relance: bool = False) -> tuple[str, str, bool]:
    cle_cache = _cle_cache_reponse_llm(prompt)
    if not forcer_relance and cle_cache in st.session_state:
        cache = st.session_state[cle_cache]
        return cache["texte"], cache["statut"], cache["api"]

    reponse_api, statut = appeler_llm(prompt)
    texte = reponse_api or generer_reponse_degonflage(payload)
    cache = {
        "texte": texte,
        "statut": statut if reponse_api else f"{statut} Réponse locale affichée en secours.",
        "api": bool(reponse_api),
    }
    st.session_state[cle_cache] = cache
    return cache["texte"], cache["statut"], cache["api"]


def _forcer_relance_reponses_llm() -> None:
    st.session_state["forcer_relance_llm_proposition"] = True


def afficher(donnees: dict) -> None:
    afficher_badge_fichier_source(__file__)
    proposition = donnees.get("proposition", {})
    payload_llm = construire_json_llm(donnees)
    prompt_llm = construire_prompt_llm(payload_llm)
    forcer_relance_llm = st.session_state.pop("forcer_relance_llm_proposition", False)
    reponse_llm, statut_llm, reponse_llm_api = _obtenir_reponse_llm(
        prompt_llm,
        payload_llm,
        forcer_relance=forcer_relance_llm,
    )
    recits_selectionnes = recits_impactants(payload_llm, 3)
    sorties_llm = extraire_sorties_llm(reponse_llm) or sorties_llm_secours(payload_llm)
    conseil_editorial = extraire_conseil_editorial(reponse_llm)
    if not conseil_editorial:
        conseil_editorial = construire_conseil_editorial_depuis_sorties(sorties_llm, payload_llm)
    brouillon_consolide = extraire_brouillon_consolide(reponse_llm)
    brouillon_interne = re.search(
        r"\b(SORTIE_LLM_|RECIT:|MOTS_CLES_DOMINANTS|RECIT_OBSERVE|ELEMENTS_RECURRENTS|SIGNAUX_POLARISATION|POINTS_A_VERIFIER|messages?|communautés?|récits?|nég\.|score|pic observé)\b",
        brouillon_consolide or "",
        re.IGNORECASE,
    )
    if not brouillon_consolide or brouillon_interne:
        brouillon_consolide = construire_brouillon_depuis_sorties(sorties_llm, payload_llm)
    if isinstance(proposition, dict) and brouillon_consolide:
        proposition["brouillon_consolide"] = brouillon_consolide
        proposition["reponse_brouillon"] = brouillon_consolide
    analyse_situation = construire_analyse_situation(sorties_llm, payload_llm)

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
    if reponse_llm_api:
        st.success(statut_llm)
    else:
        st.warning(statut_llm)

    col_relance, col_relance_info = st.columns([0.16, 0.84])
    with col_relance:
        st.button(
            "Relancer",
            key="relancer_reponses_llm",
            help="Régénérer les 3 réponses LLM et le brouillon consolidé.",
            on_click=_forcer_relance_reponses_llm,
        )
    with col_relance_info:
        st.caption("Relance discrète : nouvelle génération uniquement sur demande.")

    injecter_style_sorties_llm()
    if sorties_llm:
        for sortie in sorties_llm:
            afficher_exemples_tweets_llm(
                exemples_tweets_pour_sortie(sortie, payload_llm),
                str(sortie.get("index", "x")),
            )
            afficher_carte_sortie_llm(
                f"Sortie LLM {sortie['index']} - récit ciblé",
                sortie["recit"],
                sortie["texte"],
            )
    else:
        afficher_carte_sortie_llm(
            "Sorties LLM",
            "Réponse générée",
            reponse_llm,
        )
    afficher_carte_sortie_llm(
        "Analyse de la situation",
        "Lecture synthétique des signaux de crise",
        analyse_situation,
        final=True,
    )
    afficher_carte_sortie_llm(
        "Conseil éditorial",
        "Arbitrage proposé avant rédaction",
        conseil_editorial,
        final=True,
    )
    afficher_carte_sortie_llm(
        "Brouillon central consolidé",
        "Proposition de communiqué en réponse à la gestion de crise",
        brouillon_consolide,
        final=True,
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

    _afficher_editeur_prompt_final()
    _afficher_boite_outils_api()
