import joblib
import pandas as pd
from decouple import config

from pipeline.modules.module import Module


class AgentViralite(Module):
    def __init__(self, donnees: dict) -> None:
        super().__init__(donnees)
        self.modele = joblib.load("pipeline/models/agent_viralite_model.pkl")
        self.viralite = False

    def run(self) -> dict:
        self.viralite = False
        dataset = self.donnees.get("dataset", pd.DataFrame()).copy()

        if dataset.empty:
            self.donnees["dataset"] = dataset
            self.donnees["arreter_pipeline"] = True
            return self.donnees

        features = self.preparer_features(dataset)
        dataset["Viralite"] = self.predire_viralite(features)
        dataset["Classe_viralite"] = dataset["Viralite"].apply(self.classifier_viralite)

        self.viralite = (dataset["Classe_viralite"] == "Viral").any()
        self.donnees["dataset"] = dataset

        if not self.viralite:
            self.donnees["arreter_pipeline"] = True

        return self.donnees

    def preparer_features(self, dataset: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=dataset.index)
        features["X Followers"] = pd.to_numeric(dataset["X Followers"], errors="coerce").fillna(0)
        features["verified"] = dataset["X Verified"].fillna(False).astype(int)
        features["X Posts"] = pd.to_numeric(dataset["X Posts"], errors="coerce").fillna(0)
        features["nb_hashtags"] = dataset["Hashtags"].apply(self.compter_hashtags)
        features["longueur"] = dataset["Full Text"].fillna("").astype(str).str.len()
        return features[["X Followers", "verified", "X Posts", "nb_hashtags", "longueur"]]

    def compter_hashtags(self, hashtags) -> int:
        if pd.isna(hashtags) or str(hashtags).strip() == "":
            return 0
        return len([tag for tag in str(hashtags).split() if tag.startswith("#")])

    def predire_viralite(self, features: pd.DataFrame):
        if hasattr(self.modele, "predict_proba"):
            classes = list(getattr(self.modele, "classes_", []))
            index_viral = classes.index(1) if 1 in classes else -1
            return self.modele.predict_proba(features)[:, index_viral]

        return self.modele.predict(features)

    def classifier_viralite(self, score: float) -> str:
        seuil_haut = config("SEUIL_VIRALITE_HAUT", default=0.7, cast=float)
        seuil_moyen = config("SEUIL_VIRALITE_MOYEN", default=0.4, cast=float)

        if score >= seuil_haut:
            return "Viral"
        if score >= seuil_moyen:
            return "Moyennement Viral"
        return "Non Viral"
