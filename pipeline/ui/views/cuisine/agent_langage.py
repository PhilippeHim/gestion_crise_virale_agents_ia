"""Agent 2 — NLP narratif.

Fait émerger les récits qui structurent une crise informationnelle, à partir du
seul *schéma* du corpus (aucun identifiant de crise codé en dur). Le pipeline
interne est volontairement simple et assumé comme exploratoire :

    nettoyage léger -> déduplication -> TF-IDF (1-2 grammes) -> KMeans
    -> score de risque (volume relatif + part négative) -> RAG TF-IDF par récit.

Entrées lues dans ``donnees`` :
    - ``dataset`` : DataFrame du corpus.
    - ``nombre_recits`` (option) : nombre de clusters à extraire ; à défaut
      l'env ``NOMBRE_RECITS``, à défaut ``NOMBRE_RECITS_DEFAUT``.
    - ``mots_vides`` (option) : liste de stop words ; à défaut ``MOTS_VIDES_FR``.

Sortie écrite dans ``donnees["narratif"]`` (clés inchangées vis-à-vis des vues).
"""

import re

import numpy as np
import pandas as pd
from pipeline.config import config
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pipeline.modules.module import Module


# --- Hyperparamètres génériques (réglables par crise, jamais spécifiques au cas) ---
NOMBRE_RECITS_DEFAUT = 6          # nombre de récits à extraire ; override via donnees/env
TFIDF_MAX_FEATURES = 3000         # vocabulaire max pour le clustering
TFIDF_NGRAMMES = (1, 2)           # unigrammes + bigrammes
TFIDF_MIN_DF = 2                  # terme présent dans au moins N textes
TFIDF_MAX_DF = 0.35               # terme présent dans au plus 35 % des textes
NB_MOTS_CLES = 7                  # mots-clés retenus par récit
LONGUEUR_TEXTE_MIN = 3            # textes plus courts ignorés
RAG_MAX_FEATURES = 5000           # vocabulaire du moteur RAG
RAG_EXEMPLES_PAR_RECIT = 6        # exemples renvoyés par récit
RAG_RECITS_MAX = 5                # récits prioritaires documentés par le RAG
RAG_SIMILARITE_MIN = 0.05         # exemple écarté en dessous de ce cosinus

# --- Pondération du score de risque (méthodologie : ne pas modifier sans concertation) ---
POIDS_VOLUME = 0.6
POIDS_NEGATIVITE = 0.4
SEUIL_RISQUE_ELEVE = 60
SEUIL_RISQUE_MOYEN = 35

# --- Valeurs de sentiment attendues (comparées sans tenir compte de la casse) ---
SENTIMENT_NEGATIF = "negative"
SENTIMENT_POSITIF = "positive"
SENTIMENT_NEUTRE = "neutral"

# Colonnes texte acceptées, par ordre de préférence.
COLONNES_TEXTE = ("message_normalizer", "Full Text")

MOTS_VIDES_FR = (
    "le la les un une des de du d l et en a au aux ce que qui pour pas plus sur se sa son "
    "ses ne rt c est il elle on nous vous ils elles je tu me te y dans par avec sans mais "
    "ou donc or ni car cette cet ces leur leurs vos nos mon ma mes ton ta tes notre votre "
    "qu n s t si sont ont ca fait tout comme meme bien etre cela faire dit"
).split()


def normaliser_sentiment(serie: pd.Series) -> pd.Series:
    """Ramène une colonne de sentiment à un libellé minuscule sans espaces parasites.

    Rend la comparaison robuste à la casse et aux variantes (``"Negative"``,
    ``" NEGATIVE "``...) sans dépendre des libellés exacts d'une crise donnée.
    """
    return serie.fillna("unknown").astype(str).str.strip().str.lower()


class AgentLangage(Module):
    """Extrait, nomme, et hiérarchise les récits d'un corpus de crise."""

    def run(self) -> dict:
        dataset = self.donnees.get("dataset", pd.DataFrame())

        if dataset.empty:
            self.donnees["narratif"] = {
                "erreur": "Dataset vide ou absent.",
                "tonalite": {},
                "recits": [],
                "rag": {},
            }
            return self.donnees

        corpus = self.preparer_corpus(dataset)
        corpus_sans_doublons = self.ignorer_doublons(corpus)
        tonalite = self.analyser_tonalite(dataset)
        recits = self.analyser_recits(corpus, corpus_sans_doublons)
        rag = self.construire_rag(corpus, corpus_sans_doublons, recits)

        self.donnees["narratif"] = {
            "tonalite": tonalite,
            "recits": recits,
            "rag": rag,
            "corpus": {
                "messages_total": int(len(corpus)),
                "messages_analyses": int(len(corpus_sans_doublons)),
                "messages_ignores_car_doublons": int(len(corpus) - len(corpus_sans_doublons)),
            },
            "resume": self.resumer_narratif(tonalite, recits),
        }

        return self.donnees

    # ------------------------------------------------------------------ #
    # Préparation du corpus
    # ------------------------------------------------------------------ #
    def preparer_corpus(self, dataset: pd.DataFrame) -> pd.DataFrame:
        """Construit un corpus ``(texte, Sentiment)`` nettoyé et filtré.

        La colonne de sentiment est optionnelle : si elle est absente, une
        colonne neutre est créée pour que l'agent reste fonctionnel.
        """
        colonne_texte = self.colonne_texte(dataset)
        corpus = pd.DataFrame({"texte_brut": dataset[colonne_texte]})

        if "Sentiment" in dataset.columns:
            corpus["Sentiment"] = normaliser_sentiment(dataset["Sentiment"])
        else:
            corpus["Sentiment"] = "unknown"

        corpus["texte"] = corpus["texte_brut"].fillna("").astype(str).apply(self.nettoyer_texte)
        corpus = corpus[corpus["texte"].str.len() > LONGUEUR_TEXTE_MIN]
        return corpus[["texte", "Sentiment"]].copy()

    def ignorer_doublons(self, corpus: pd.DataFrame) -> pd.DataFrame:
        """Garde un seul exemplaire de chaque texte (les doublons servent au volume)."""
        return corpus.drop_duplicates(subset=["texte"], keep="first").copy()

    def colonne_texte(self, dataset: pd.DataFrame) -> str:
        """Renvoie la première colonne texte disponible selon le schéma."""
        for colonne in COLONNES_TEXTE:
            if colonne in dataset.columns:
                return colonne
        raise KeyError(
            f"Aucune colonne texte trouvée : attendu l'une de {COLONNES_TEXTE}."
        )

    def nettoyer_texte(self, texte: str) -> str:
        """Nettoyage léger : retire les URLs et normalise les espaces."""
        texte = re.sub(r"http\S+|www\.\S+", " ", str(texte))
        texte = re.sub(r"\s+", " ", texte)
        return texte.strip()

    # ------------------------------------------------------------------ #
    # Tonalité globale
    # ------------------------------------------------------------------ #
    def analyser_tonalite(self, dataset: pd.DataFrame) -> dict:
        """Répartition du sentiment et parts négative / positive / neutre."""
        if "Sentiment" not in dataset.columns:
            return {"erreur": "Colonne Sentiment absente."}

        sentiment = normaliser_sentiment(dataset["Sentiment"])
        repartition = sentiment.value_counts()
        total = int(repartition.sum())

        return {
            "total_messages": total,
            "repartition": repartition.astype(int).to_dict(),
            "pourcentages": (repartition / total * 100).round(1).to_dict() if total else {},
            "part_negative": round(float((sentiment == SENTIMENT_NEGATIF).mean() * 100), 1),
            "part_positive": round(float((sentiment == SENTIMENT_POSITIF).mean() * 100), 1),
            "part_neutral": round(float((sentiment == SENTIMENT_NEUTRE).mean() * 100), 1),
        }

    # ------------------------------------------------------------------ #
    # Extraction des récits
    # ------------------------------------------------------------------ #
    def nombre_recits(self, plafond: int) -> int:
        """Nombre de clusters voulu, borné par le nombre de textes disponibles.

        Priorité : ``donnees["nombre_recits"]`` > env ``NOMBRE_RECITS`` >
        ``NOMBRE_RECITS_DEFAUT``. Aucune valeur spécifique au cas n'est figée
        dans la logique de l'agent.
        """
        demande = self.donnees.get("nombre_recits")
        if demande is None:
            demande = config("NOMBRE_RECITS", default=NOMBRE_RECITS_DEFAUT, cast=int)
        return min(int(demande), plafond)

    def analyser_recits(
        self, corpus: pd.DataFrame, corpus_sans_doublons: pd.DataFrame
    ) -> list[dict]:
        """Clusterise les textes uniques en récits, puis les qualifie."""
        textes_analyse = corpus_sans_doublons["texte"].tolist()
        if len(textes_analyse) < 2:
            return []

        nombre_recits = self.nombre_recits(plafond=len(textes_analyse))
        mots_vides = self.donnees.get("mots_vides", MOTS_VIDES_FR)

        vectoriseur = TfidfVectorizer(
            max_features=TFIDF_MAX_FEATURES,
            ngram_range=TFIDF_NGRAMMES,
            min_df=TFIDF_MIN_DF,
            max_df=TFIDF_MAX_DF,
            stop_words=mots_vides,
        )
        matrice = vectoriseur.fit_transform(textes_analyse)
        labels = KMeans(
            n_clusters=nombre_recits, random_state=42, n_init=10
        ).fit_predict(matrice)
        termes = np.array(vectoriseur.get_feature_names_out())

        volumes = corpus["texte"].value_counts()
        part_negative_par_texte = corpus.groupby("texte")["Sentiment"].apply(
            lambda serie: (serie == SENTIMENT_NEGATIF).mean()
        )

        recits = []
        for identifiant in sorted(set(labels)):
            indices = np.where(labels == identifiant)[0]
            textes_cluster = [textes_analyse[index] for index in indices]
            centroide = np.asarray(matrice[indices].mean(axis=0)).ravel()
            mots_cles = termes[centroide.argsort()[::-1][:NB_MOTS_CLES]].tolist()
            volume = int(volumes[textes_cluster].sum())
            pct_negative = float(
                np.mean([part_negative_par_texte.get(texte, 0.0) for texte in textes_cluster]) * 100
            )
            exemple = max(textes_cluster, key=lambda texte: volumes[texte])

            recits.append(
                {
                    "id": int(identifiant),
                    "nom": ", ".join(mots_cles[:3]),
                    "mots_cles": mots_cles,
                    "exemple": exemple[:240],
                    "messages_analyses": int(len(textes_cluster)),
                    "volume": volume,
                    "pct_negative": round(pct_negative, 1),
                }
            )

        return self.ajouter_risque(recits)

    def ajouter_risque(self, recits: list[dict]) -> list[dict]:
        """Calcule le score de risque (volume relatif + négativité) et trie."""
        if not recits:
            return []

        volume_max = max(recit["volume"] for recit in recits) or 1
        for recit in recits:
            score = 100 * (
                POIDS_VOLUME * (recit["volume"] / volume_max)
                + POIDS_NEGATIVITE * (recit["pct_negative"] / 100)
            )
            recit["score_risque"] = round(score, 1)
            if score >= SEUIL_RISQUE_ELEVE:
                recit["niveau_risque"] = "eleve"
            elif score >= SEUIL_RISQUE_MOYEN:
                recit["niveau_risque"] = "moyen"
            else:
                recit["niveau_risque"] = "faible"

        return sorted(recits, key=lambda recit: recit["score_risque"], reverse=True)

    # ------------------------------------------------------------------ #
    # RAG : exemples représentatifs par récit
    # ------------------------------------------------------------------ #
    def construire_rag(
        self,
        corpus: pd.DataFrame,
        corpus_sans_doublons: pd.DataFrame,
        recits: list[dict],
    ) -> dict:
        """Pour chaque récit prioritaire, remonte des messages représentatifs.

        Score = similarité cosinus TF-IDF pondérée par ``log(volume)``, afin de
        privilégier des exemples à la fois proches du récit et réellement diffusés.
        """
        volumes = corpus["texte"].value_counts()
        documents = corpus_sans_doublons["texte"].tolist()

        if len(documents) < 2:
            return {"documents": len(documents), "exemples_par_recit": {}}

        vectoriseur = TfidfVectorizer(
            max_features=RAG_MAX_FEATURES, ngram_range=TFIDF_NGRAMMES, min_df=TFIDF_MIN_DF
        )
        matrice = vectoriseur.fit_transform(documents)
        volumes_documents = np.log1p([volumes[document] for document in documents])

        exemples = {}
        for recit in recits[:RAG_RECITS_MAX]:
            requete = f"{recit['nom']} {' '.join(recit['mots_cles'])} {recit['exemple']}"
            vecteur_requete = vectoriseur.transform([self.nettoyer_texte(requete)])
            similarites = cosine_similarity(vecteur_requete, matrice).ravel()
            score = similarites * volumes_documents
            meilleurs = score.argsort()[::-1][:RAG_EXEMPLES_PAR_RECIT]
            exemples[str(recit["id"])] = [
                {
                    "message": documents[index],
                    "volume": int(volumes[documents[index]]),
                    "similarite": round(float(similarites[index]), 3),
                }
                for index in meilleurs
                if similarites[index] >= RAG_SIMILARITE_MIN
            ]

        return {"documents": len(documents), "exemples_par_recit": exemples}

    # ------------------------------------------------------------------ #
    # Résumé
    # ------------------------------------------------------------------ #
    def resumer_narratif(self, tonalite: dict, recits: list[dict]) -> str:
        """Phrase de synthèse pour l'orchestrateur et la vue cuisine."""
        if not recits:
            return "Aucun récit exploitable détecté."

        recit_principal = recits[0]
        return (
            f"{len(recits)} récits détectés. "
            f"Récit principal: {recit_principal['nom']} "
            f"({recit_principal['volume']} messages, risque {recit_principal['niveau_risque']}). "
            f"Part négative corpus: {tonalite.get('part_negative', 'n/a')}%."
        )
