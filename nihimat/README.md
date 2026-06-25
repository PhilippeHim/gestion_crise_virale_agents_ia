# Cellule de veille & réponse de crise informationnelle

Système générique (3 agents + orchestrateur) d'analyse d'une crise sur X et de génération
de réponses institutionnelles. **Principe « test Coca »** : aucun identifiant de cas codé en
dur, tout est piloté par `SchemaConfig` — change le mapping de colonnes et ça tourne sur un
autre corpus / une autre organisation.

## Agents
- **Veille** — pics (z-score robuste), déclencheur (patient zéro), amplificateurs, concentration. *Sans LLM.*
- **Narratif** — communautés (Louvain co-amplification) + récits (dédup → TF-IDF/embeddings → KMeans) + risque déterministe. *LLM optionnel pour nommer/justifier.*
- **Rédacteur** — réponse neutre par récit, ancrée dans le corpus (RAG), à valider. *LLM requis pour générer.*
- **Orchestrateur** — Veille → Narratif → Rédacteur → validation humaine.

## Installation
```bash
pip install -r requirements.txt
```

## Usage (Python / Colab)
```python
from crisis_agents import Orchestrateur, LLMClient
import pandas as pd, os

df = pd.read_excel("data.xlsx")
os.environ["GEMINI_API_KEY"] = "..."           # optionnel

report = Orchestrateur(method="tfidf", k=6,
                       llm=LLMClient("gemini")  # ou None / "mistral" / "anthropic" / "openai"
                      ).run(df, institutional_account="LeCNC", organization="Le CNC")
print(report.brief)
```
> Colab : déposer `crisis_agents.py` (fichier unique) à la racine `/content`. Aucun dossier requis.

## Démo
```bash
streamlit run app.py
```
Charge le `.xlsx`, choisis la méthode/k, (optionnel) renseigne un fournisseur LLM + clé,
puis valide/édite les réponses dans l'onglet **Réponses**.

## Limites assumées
Co-amplification ≠ contagion prouvée (pas de graphe d'abonnements) · silhouette des récits
faible (clustering exploratoire) · corpus asymétrique (le ton hérite du biais des données).
