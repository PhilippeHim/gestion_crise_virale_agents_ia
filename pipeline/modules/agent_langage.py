import re

import numpy as np
import pandas as pd
from decouple import config
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pipeline.modules.module import Module


MOTS_VIDES_FR = (
    "le la les un une des de du d l et en a au aux ce que qui pour pas plus sur se sa son "
    "ses ne rt c est il elle on nous vous ils elles je tu me te y dans par avec sans mais "
    "ou donc or ni car cette cet ces leur leurs vos nos mon ma mes ton ta tes notre votre "
    "qu n s t si sont ont ca fait tout comme meme bien etre cela faire dit"
).split()


class AgentLangage(Module):
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

    def preparer_corpus(self, dataset: pd.DataFrame) -> pd.DataFrame:
        colonne_texte = self.colonne_texte(dataset)
        corpus = dataset[[colonne_texte, "Sentiment"]].copy()
        corpus["texte"] = corpus[colonne_texte].fillna("").astype(str).apply(self.nettoyer_texte)
        corpus = corpus[corpus["texte"].str.len() > 3]
        return corpus

    def ignorer_doublons(self, corpus: pd.DataFrame) -> pd.DataFrame:
        return corpus.drop_duplicates(subset=["texte"], keep="first").copy()

    def colonne_texte(self, dataset: pd.DataFrame) -> str:
        for colonne in ["message_normalizer", "Full Text"]:
            if colonne in dataset.columns:
                return colonne
        raise KeyError("Aucune colonne texte trouvée: attendu message_normalizer ou Full Text.")

    def nettoyer_texte(self, texte: str) -> str:
        texte = re.sub(r"http\S+|www\.\S+", " ", str(texte))
        texte = re.sub(r"\s+", " ", texte)
        return texte.strip()

    def analyser_tonalite(self, dataset: pd.DataFrame) -> dict:
        if "Sentiment" not in dataset.columns:
            return {"erreur": "Colonne Sentiment absente."}

        repartition = dataset["Sentiment"].fillna("unknown").value_counts()
        total = int(repartition.sum())

        return {
            "total_messages": total,
            "repartition": repartition.astype(int).to_dict(),
            "pourcentages": (repartition / total * 100).round(1).to_dict() if total else {},
            "part_negative": round(float((dataset["Sentiment"] == "negative").mean() * 100), 1),
            "part_positive": round(float((dataset["Sentiment"] == "positive").mean() * 100), 1),
            "part_neutral": round(float((dataset["Sentiment"] == "neutral").mean() * 100), 1),
        }

    def analyser_recits(self, corpus: pd.DataFrame, corpus_sans_doublons: pd.DataFrame) -> list[dict]:
        textes_analyse = corpus_sans_doublons["texte"].tolist()
        if len(textes_analyse) < 2:
            return []

        nombre_recits = min(config("NOMBRE_RECITS", default=6, cast=int), len(textes_analyse))
        vectoriseur = TfidfVectorizer(
            max_features=3000,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.35,
            stop_words=MOTS_VIDES_FR,
        )
        matrice = vectoriseur.fit_transform(textes_analyse)
        labels = KMeans(n_clusters=nombre_recits, random_state=42, n_init=10).fit_predict(matrice)
        termes = np.array(vectoriseur.get_feature_names_out())
        volumes = corpus["texte"].value_counts()
        sentiment_par_texte = corpus.groupby("texte")["Sentiment"].apply(
            lambda serie: (serie == "negative").mean()
        )

        recits = []
        for identifiant in sorted(set(labels)):
            indices = np.where(labels == identifiant)[0]
            textes_cluster = [textes_analyse[index] for index in indices]
            centroide = np.asarray(matrice[indices].mean(axis=0)).ravel()
            mots_cles = termes[centroide.argsort()[::-1][:7]].tolist()
            volume = int(volumes[textes_cluster].sum())
            pct_negative = float(np.mean([sentiment_par_texte.get(texte, 0.0) for texte in textes_cluster]) * 100)
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
        if not recits:
            return []

        volume_max = max(recit["volume"] for recit in recits) or 1
        for recit in recits:
            score = 100 * (
                0.6 * (recit["volume"] / volume_max)
                + 0.4 * (recit["pct_negative"] / 100)
            )
            recit["score_risque"] = round(score, 1)
            if score >= 60:
                recit["niveau_risque"] = "eleve"
            elif score >= 35:
                recit["niveau_risque"] = "moyen"
            else:
                recit["niveau_risque"] = "faible"

        return sorted(recits, key=lambda recit: recit["score_risque"], reverse=True)

    def construire_rag(
        self,
        corpus: pd.DataFrame,
        corpus_sans_doublons: pd.DataFrame,
        recits: list[dict],
    ) -> dict:
        volumes = corpus["texte"].value_counts()
        documents = corpus_sans_doublons["texte"].tolist()

        if len(documents) < 2:
            return {"documents": len(documents), "exemples_par_recit": {}}

        vectoriseur = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=2)
        matrice = vectoriseur.fit_transform(documents)

        exemples = {}
        for recit in recits[:5]:
            requete = f"{recit['nom']} {' '.join(recit['mots_cles'])} {recit['exemple']}"
            vecteur_requete = vectoriseur.transform([self.nettoyer_texte(requete)])
            similarites = cosine_similarity(vecteur_requete, matrice).ravel()
            score = similarites * np.log1p([volumes[document] for document in documents])
            meilleurs = score.argsort()[::-1][:6]
            exemples[str(recit["id"])] = [
                {
                    "message": documents[index],
                    "volume": int(volumes[documents[index]]),
                    "similarite": round(float(similarites[index]), 3),
                }
                for index in meilleurs
                if similarites[index] >= 0.05
            ]

        return {
            "documents": len(documents),
            "exemples_par_recit": exemples,
        }

    def resumer_narratif(self, tonalite: dict, recits: list[dict]) -> str:
        if not recits:
            return "Aucun récit exploitable détecté."

        recit_principal = recits[0]
        return (
            f"{len(recits)} récits détectés. "
            f"Récit principal: {recit_principal['nom']} "
            f"({recit_principal['volume']} messages, risque {recit_principal['niveau_risque']}). "
            f"Part négative corpus: {tonalite.get('part_negative', 'n/a')}%."
        )
