import re

import pandas as pd

from pipeline.modules.module import Module


def extraire_auteur_source(url) -> str | None:
    if pd.isna(url):
        return None

    match = re.search(r"twitter\.com/([^/]+)/status", str(url))
    return match.group(1).lower() if match else None


def extraire_status_id(url) -> str | None:
    if pd.isna(url):
        return None

    match = re.search(r"status[es]*/(\d+)", str(url))
    return match.group(1) if match else None


class ChargementDataset(Module):
    '''
    Module responsable de charger le dataset à partir d'un fichier XLSX.
    '''

    def run(self) -> dict:
        path = self.donnees.get("path")

        if path:
            dataset = pd.read_excel(path)
            self.donnees["dataset"] = self.preparer_dataset(dataset)

        return self.donnees

    def preparer_dataset(self, dataset: pd.DataFrame) -> pd.DataFrame:
        dataset = dataset.copy()

        if "Date" in dataset.columns:
            dataset["Date"] = pd.to_datetime(dataset["Date"], errors="coerce")

        if "X Repost of" in dataset.columns:
            dataset["_source"] = dataset["X Repost of"].apply(extraire_auteur_source)
            dataset["_source_status_id"] = dataset["X Repost of"].apply(extraire_status_id)
        else:
            dataset["_source"] = None
            dataset["_source_status_id"] = None

        if "Url" in dataset.columns:
            dataset["_status_id"] = dataset["Url"].apply(extraire_status_id)
        else:
            dataset["_status_id"] = None

        if "Engagement Type" in dataset.columns:
            dataset["_is_original"] = dataset["Engagement Type"].isna()
        else:
            dataset["_is_original"] = True

        return dataset
