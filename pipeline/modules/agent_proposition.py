import pandas as pd

from pipeline.modules.module import Module


class AgentProposition(Module):
    def run(self) -> dict:
        self.donnees["proposition"] = self.construire_proposition()
        return self.donnees

    def construire_proposition(self) -> dict:
        dataset = self.donnees.get("dataset", pd.DataFrame())
        narratif = self.donnees.get("narratif", {})
        recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
        tonalite = narratif.get("tonalite", {}) if isinstance(narratif, dict) else {}
        concentration = self.donnees.get("concentration", {})
        amplificateurs = self.donnees.get("amplificateurs", pd.DataFrame())

        recit_prioritaire = self.recit_prioritaire(recits)
        recit_visible = max(recits, key=lambda recit: recit.get("volume", 0), default=None)
        pic = self.pic_volume(dataset)
        top_amplificateurs = self.top_amplificateurs(amplificateurs)

        niveau_risque = "élevé" if recit_prioritaire and recit_prioritaire.get("niveau_risque") == "eleve" else "modéré"
        strategie = "Clarification factuelle"

        return {
            "titre": "Crise informationnelle CNC x Ultia",
            "public_cible": "Rédaction, direction de la communication, porte-parole",
            "priorite": "Haute" if niveau_risque == "élevé" else "Moyenne",
            "niveau_risque": niveau_risque,
            "strategie": strategie,
            "delai_recommande": "Sous 2 heures après validation interne",
            "synthese_executive": self.synthese_executive(
                dataset=dataset,
                pic=pic,
                recits=recits,
                recit_prioritaire=recit_prioritaire,
                tonalite=tonalite,
            ),
            "diagnostic": [
                "La crise est structurée par plusieurs récits concurrents, pas par un seul message isolé.",
                "Le volume visible doit être croisé avec la tonalité négative pour prioriser la réponse.",
                "La réponse recommandée doit rester factuelle, sobre et non personnalisée.",
            ],
            "chiffres_cles": {
                "messages_analyses": int(len(dataset)) if isinstance(dataset, pd.DataFrame) else 0,
                "pic": pic,
                "nombre_recits": int(len(recits)),
                "part_negative": tonalite.get("part_negative"),
                "gini_contenu": concentration.get("gini_contenu"),
                "top20_share_pct": concentration.get("top20_share_pct"),
                "top_amplificateurs": top_amplificateurs,
            },
            "recit_prioritaire": self.formater_recit(recit_prioritaire),
            "recit_le_plus_visible": self.formater_recit(recit_visible),
            "messages_cles": [
                "Reconnaître la préoccupation exprimée sans reprendre les formulations polémiques.",
                "Rappeler que les décisions et dispositifs doivent être expliqués à partir de faits validés.",
                "Éviter toute attaque personnelle ou toute réponse émotionnelle.",
            ],
            "reponse_brouillon": self.reponse_brouillon(recit_prioritaire),
            "messages_a_eviter": [
                "Attaques personnelles contre des comptes ou influenceurs.",
                "Promesses non validées par la direction ou le juridique.",
                "Formulations défensives qui donnent l'impression de répondre sous pression.",
            ],
            "points_a_valider": [
                "Position officielle de l'institution.",
                "Faits internes validés sur le dossier concerné.",
                "Validation juridique du message.",
                "Canal de publication et porte-parole.",
            ],
            "notice_validation": (
                "Document de travail interne. Aucune publication ne doit être faite sans validation "
                "humaine, direction et juridique."
            ),
        }

    def recit_prioritaire(self, recits: list[dict]) -> dict | None:
        if not recits:
            return None
        return max(
            recits,
            key=lambda recit: (
                recit.get("score_risque", 0),
                recit.get("pct_negative", 0),
                recit.get("volume", 0),
            ),
        )

    def pic_volume(self, dataset: pd.DataFrame) -> dict:
        if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Date" not in dataset.columns:
            return {"date": "n/a", "messages": 0}

        quotidien = dataset.set_index("Date").resample("D").size()
        if quotidien.empty:
            return {"date": "n/a", "messages": 0}

        date_pic = quotidien.idxmax()
        return {"date": f"{date_pic:%Y-%m-%d}", "messages": int(quotidien.max())}

    def top_amplificateurs(self, amplificateurs) -> list[dict]:
        if not isinstance(amplificateurs, pd.DataFrame) or amplificateurs.empty:
            return []
        colonnes = [col for col in ["source", "retweets", "part_pct"] if col in amplificateurs.columns]
        return amplificateurs[colonnes].head(5).to_dict("records")

    def formater_recit(self, recit: dict | None) -> dict:
        if not recit:
            return {}
        return {
            "nom": recit.get("nom"),
            "volume": recit.get("volume"),
            "pct_negative": recit.get("pct_negative"),
            "score_risque": recit.get("score_risque"),
            "niveau_risque": recit.get("niveau_risque"),
            "mots_cles": recit.get("mots_cles", [])[:5],
            "exemple": recit.get("exemple"),
        }

    def synthese_executive(
        self,
        dataset: pd.DataFrame,
        pic: dict,
        recits: list[dict],
        recit_prioritaire: dict | None,
        tonalite: dict,
    ) -> str:
        messages = int(len(dataset)) if isinstance(dataset, pd.DataFrame) else 0
        recit_nom = recit_prioritaire.get("nom") if recit_prioritaire else "récit prioritaire non détecté"
        pct_negative = tonalite.get("part_negative", "n/a")
        return (
            f"{messages:,} messages ont été analysés. Le pic de volume intervient le "
            f"{pic.get('date')} avec {pic.get('messages')} messages. La crise est structurée "
            f"par {len(recits)} récits principaux. Le récit à traiter en priorité est "
            f"« {recit_nom} », car son score de risque combine volume et tonalité négative. "
            f"La part négative globale du corpus est de {pct_negative}%."
        )

    def reponse_brouillon(self, recit_prioritaire: dict | None) -> str:
        recit = recit_prioritaire.get("nom") if recit_prioritaire else "le récit prioritaire identifié"
        return (
            "Le CNC a pris connaissance des réactions suscitées par la situation actuelle. "
            f"Les échanges observés font apparaître un point d'attention prioritaire autour de « {recit} ». "
            "Notre réponse doit s'appuyer uniquement sur des faits validés et rappeler le cadre dans lequel "
            "les dispositifs concernés sont instruits. "
            "[Position institutionnelle officielle requise]. "
            "[Informations factuelles validées requises]. "
            "Ce message doit être validé par la direction et le service juridique avant toute publication."
        )
