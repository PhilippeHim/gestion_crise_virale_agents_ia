import numpy as np
import pandas as pd
import plotly.express as px
from decouple import config

from pipeline.modules.module import Module


class Declencheur(Module):
    def run(self) -> dict:
        pas_de_declencheur = True
        seuil_impression = config("SEUIL_IMPRESSION", default=5000, cast=int)

        for _, ligne in self.donnees.get("dataset", pd.DataFrame()).iterrows():
            if ligne["Impressions"] > seuil_impression:
                pas_de_declencheur = False
                break

        if pas_de_declencheur:
            print(f"Pas de déclencheur trouvé, seuil d'impression: {seuil_impression}")
            self.donnees["arreter_pipeline"] = True

        self.donnees["concentration"] = self.calculer_concentration()
        self.donnees["amplificateurs"] = self.calculer_amplificateurs()
        self.donnees["graphique_gini"] = self.graphique_gini()
        self.donnees["graphique_amplificateurs"] = self.graphique_amplificateurs_principaux()

        return self.donnees

    def calculer_gini(self, valeurs) -> float:
        valeurs = np.sort(np.asarray(valeurs, dtype=float))

        if len(valeurs) == 0 or valeurs.sum() == 0:
            return float("nan")

        cumul = np.cumsum(valeurs)
        return float((len(valeurs) + 1 - 2 * np.sum(cumul) / cumul[-1]) / len(valeurs))

    def calculer_amplificateurs(self) -> pd.DataFrame:
        dataset = self.donnees.get("dataset", pd.DataFrame())

        if dataset.empty or "_source" not in dataset.columns:
            return pd.DataFrame(columns=["source", "retweets", "part_pct"])

        sources = dataset["_source"].dropna().value_counts()

        if sources.empty:
            return pd.DataFrame(columns=["source", "retweets", "part_pct"])

        amplificateurs = sources.rename("retweets").to_frame()
        amplificateurs["part_pct"] = (amplificateurs["retweets"] / sources.sum() * 100).round(1)
        amplificateurs.index.name = "source"

        return amplificateurs.reset_index()

    def calculer_concentration(self) -> dict:
        dataset = self.donnees.get("dataset", pd.DataFrame())

        if dataset.empty:
            return {
                "gini_contenu": float("nan"),
                "gini_relais": float("nan"),
                "top20_share_pct": float("nan"),
            }

        sources = (
            dataset["_source"].dropna().value_counts()
            if "_source" in dataset.columns
            else pd.Series(dtype=int)
        )
        relais = (
            dataset.loc[dataset["Engagement Type"] == "RETWEET", "Author"].value_counts()
            if {"Engagement Type", "Author"}.issubset(dataset.columns)
            else pd.Series(dtype=int)
        )

        top20_share = float("nan")
        if not sources.empty and sources.sum() > 0:
            top20_share = float(round(sources.head(20).sum() / sources.sum() * 100, 1))

        return {
            "gini_contenu": round(self.calculer_gini(sources.values), 3),
            "gini_relais": round(self.calculer_gini(relais.values), 3),
            "top20_share_pct": top20_share,
        }

    def graphique_gini(self):
        concentration = self.calculer_concentration()
        donnees_gini = pd.DataFrame(
            [
                {"metrique": "Gini contenu", "valeur": concentration["gini_contenu"]},
                {"metrique": "Gini relais", "valeur": concentration["gini_relais"]},
            ]
        )

        return px.bar(
            donnees_gini,
            x="metrique",
            y="valeur",
            range_y=[0, 1],
            text="valeur",
            title="Concentration des contenus et relais",
        )

    def graphique_amplificateurs_principaux(self, top_n: int = 10):
        amplificateurs = self.calculer_amplificateurs().head(top_n)

        return px.bar(
            amplificateurs.iloc[::-1],
            x="retweets",
            y="source",
            orientation="h",
            text="retweets",
            hover_data=["part_pct"],
            title="Amplificateurs principaux",
        )
