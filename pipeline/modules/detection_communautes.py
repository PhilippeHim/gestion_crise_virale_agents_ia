import collections

import networkx as nx
import pandas as pd
from decouple import config
from networkx.algorithms.community import louvain_communities, modularity

from pipeline.modules.agent_langage import AgentLangage
from pipeline.modules.module import Module


class DetectionCommunautes(Module):
    def run(self) -> dict:
        dataset = self.donnees.get("dataset", pd.DataFrame())

        if dataset.empty:
            self.donnees["communaute"] = {
                "erreur": "Dataset vide ou absent.",
                "communautes": [],
            }
            return self.donnees

        seuil_messages = config("SEUIL_MESSAGES_COMMUNAUTE", default=500, cast=int)
        graphe, total_sources = self.construire_graphe_coamplification(dataset)

        if graphe.number_of_nodes() == 0:
            self.donnees["communaute"] = {
                "erreur": "Aucune communauté détectable.",
                "communautes": [],
                "seuil_messages": seuil_messages,
            }
            return self.donnees

        partition, modularite = self.detecter_partition(graphe)
        correspondance_auteur_communaute = {
            noeud[1]: communaute
            for noeud, communaute in partition.items()
            if noeud[0] == "u"
        }

        communautes = self.caracteriser_communautes(
            dataset,
            partition,
            correspondance_auteur_communaute,
            total_sources,
            seuil_messages,
        )

        self.donnees["communaute"] = {
            "seuil_messages": seuil_messages,
            "modularite": round(float(modularite), 3),
            "nombre_communautes_detectees": int(len(set(partition.values()))),
            "nombre_auteurs_communautarises": int(len(correspondance_auteur_communaute)),
            "communautes": communautes,
        }
        self.donnees["communautes"] = communautes

        return self.donnees

    def construire_graphe_coamplification(self, dataset: pd.DataFrame, min_rt: int = 10):
        retweets = dataset[
            (dataset["Engagement Type"] == "RETWEET")
            & dataset["_source"].notna()
        ]
        total_sources = retweets["_source"].value_counts()
        sources_retenues = set(total_sources[total_sources >= min_rt].index)
        liens = (
            retweets[retweets["_source"].isin(sources_retenues)]
            .groupby(["Author", "_source"])
            .size()
            .reset_index(name="poids")
        )

        graphe = nx.Graph()
        for _, ligne in liens.iterrows():
            graphe.add_edge(("u", ligne["Author"]), ("s", ligne["_source"]), weight=ligne["poids"])

        if graphe.number_of_nodes() == 0:
            return graphe, total_sources

        composante_principale = max(nx.connected_components(graphe), key=len)
        return graphe.subgraph(composante_principale).copy(), total_sources

    def detecter_partition(self, graphe):
        communautes = louvain_communities(graphe, weight="weight", seed=42)
        partition = {
            noeud: identifiant
            for identifiant, communaute in enumerate(communautes)
            for noeud in communaute
        }
        return partition, modularity(graphe, communautes, weight="weight")

    def caracteriser_communautes(
        self,
        dataset: pd.DataFrame,
        partition: dict,
        correspondance_auteur_communaute: dict,
        total_sources: pd.Series,
        seuil_messages: int,
    ) -> list[dict]:
        retweets = dataset[
            (dataset["Engagement Type"] == "RETWEET")
            & dataset["Author"].isin(correspondance_auteur_communaute)
        ].copy()
        retweets["_communaute"] = retweets["Author"].map(correspondance_auteur_communaute)

        tailles = collections.Counter(correspondance_auteur_communaute.values())
        sources_par_communaute = collections.defaultdict(collections.Counter)
        for noeud, communaute in partition.items():
            if noeud[0] == "s":
                sources_par_communaute[communaute][noeud[1]] = int(total_sources.get(noeud[1], 0))

        communautes = []
        for identifiant, nombre_retweeteurs in tailles.most_common():
            messages_communaute = retweets[retweets["_communaute"] == identifiant]
            nombre_messages = int(len(messages_communaute))
            if nombre_messages < seuil_messages:
                continue

            auteurs_communaute = [
                auteur
                for auteur, communaute in correspondance_auteur_communaute.items()
                if communaute == identifiant
            ]
            dataset_communaute = dataset[dataset["Author"].isin(auteurs_communaute)].copy()

            communautes.append(
                {
                    "id": int(identifiant),
                    "nombre_retweeteurs": int(nombre_retweeteurs),
                    "nombre_messages": nombre_messages,
                    "sources_pivots": sources_par_communaute[identifiant].most_common(3),
                    "pct_negative": round(float((messages_communaute["Sentiment"] == "negative").mean() * 100), 1),
                    "pct_verified": round(float(messages_communaute["X Verified"].mean() * 100), 1),
                    "jour_pic": self.jour_pic(messages_communaute),
                    "narratif": self.analyser_langage_communaute(dataset_communaute),
                }
            )

        return communautes

    def jour_pic(self, messages: pd.DataFrame) -> str:
        if messages.empty or "Date" not in messages.columns:
            return "n/a"

        quotidien = messages.set_index("Date").resample("D").size()
        return f"{quotidien.idxmax():%Y-%m-%d}" if len(quotidien) else "n/a"

    def analyser_langage_communaute(self, dataset_communaute: pd.DataFrame) -> dict:
        donnees_communaute = {
            "dataset": dataset_communaute,
            "arreter_pipeline": False,
        }
        return AgentLangage(donnees_communaute).run().get("narratif", {})
