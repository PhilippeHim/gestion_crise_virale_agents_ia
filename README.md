# NACHOS — Cuisine Agent

**N**eutralisation **A**gent for **C**risis - **H**uman-in-the-loop **O**rchestration **S**ystem

> Projet datathon NEXA 2026 — Groupe PX8  
> *Anticiper et réagir à une crise virale de communication sur X*

---

## Vue d'ensemble

NACHOS est un pipeline agentique de détection et de gestion de crises informationnelles sur X (Twitter). Il analyse un corpus de tweets, détecte les signaux d'alerte, identifie les acteurs et les récits structurants, et produit une proposition de réponse opérationnelle à destination des équipes communication.

```
Fichier XLSX
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│                   Pipeline AgentX                       │
│                                                         │
│  1. Chargement dataset    → nettoyage & normalisation   │
│  2. Déclencheur           → Gini, amplificateurs, seuil │
│  3. Agent Viralité        → scoring ML par tweet        │
│  4. Détection communautés → Louvain, clustering         │
│  5. Agent Langage         → TF-IDF, KMeans, récits, RAG │
│  6. Agent Proposition     → synthèse & brouillon        │
└─────────────────────────────────────────────────────────┘
     │
     ▼
Interface Streamlit
  ├── Vue Cuisine  (analyse technique, 11 écrans)
  └── Vue Client   (synthèse exécutive décisionnelle)
```

---

## Interface

### Vue Cuisine — Analyse agentique

Navigation par timeline en 11 écrans :

| Écran | Contenu |
|---|---|
| Collecte & filtres | Import, nettoyage, exploration du dataset |
| Déclencheurs | Gini, concentration, amplificateurs, seuil d'alerte |
| Agent 1 — Viralité | Scoring par impressions / likes / shares |
| Communautés | Détection de clusters (Louvain), polarisation |
| Agent 2 — Narratifs | Récits structurants, mots-clés, exemples |
| Filtre Risque | Significativité, manipulation, score de risque |
| Sémantique | Tonalité, sentiment, RAG |
| Coordination | Synchronies, comportements suspects |
| Proposition | Stratégie recommandée, délai, récit prioritaire |
| Proposition finale | Vue consolidée de la proposition |

### Vue Client — Synthèse exécutive

Dashboard décisionnel à destination de la direction et des équipes communication :

- **KPIs** — messages analysés, pic maximal, récits structurants, niveau de priorité
- **Synthèse executive** — diagnostic narratif de la crise
- **Priorité de communication** — stratégie et récit prioritaire
- **Signaux de coordination** — communautés détectées, part négative
- **Repères visuels** — volume quotidien et tonalité au fil du temps
- **Proposition de communiqué** — brouillon de réponse opérationnel
- **Chat IA (Gemini)** — assistant contextuel alimenté silencieusement par les sorties du pipeline
- **À éviter / À valider** — points de vigilance avant publication

---

## Installation

### Prérequis

- Python 3.10+
- Conda (recommandé)

### Environnement

```bash
conda create -n datathon_px8 python=3.11
conda activate datathon_px8
pip install -r requirements.txt
pip install google-genai
```

### Variables d'environnement

Créer un fichier `.env` à la racine du projet :

```env
GEMINI_API_KEY=votre_clé_google_ai_studio

# Seuils optionnels (valeurs par défaut utilisées si absent)
SEUIL_IMPRESSION=5000
SEUIL_MESSAGES_COMMUNAUTE=10
NOMBRE_RECITS=6
SEUIL_VIRALITE_HAUT=80
SEUIL_VIRALITE_MOYEN=40
```

La clé Gemini est obtenue gratuitement sur [aistudio.google.com](https://aistudio.google.com).

---

## Lancement

```bash
conda run -n datathon_px8 streamlit run streamlit_pipeline.py
```

Ou depuis l'environnement conda activé :

```bash
streamlit run streamlit_pipeline.py
```

---

## Données attendues

Le pipeline accepte un fichier **XLSX** au format Meltwater (ou équivalent) avec les colonnes suivantes :

| Colonne | Description |
|---|---|
| `Date` | Horodatage du message |
| `Full Text` | Texte complet du tweet |
| `Author` | Nom de compte |
| `Sentiment` | `positive` / `neutral` / `negative` |
| `Impressions` | Portée estimée |
| `Likes` | Nombre de likes |
| `Comments` | Nombre de commentaires |
| `Shares` | Nombre de partages |
| `Engagement Type` | `ORIGINAL` / `RETWEET` / … |
| `X Followers` | Abonnés de l'auteur |
| `X Verified` | Compte certifié |
| `Hashtags` | Hashtags extraits |
| `Reach` | Reach potentiel |

---

## Structure du projet

```
datathon_PX8/
├── streamlit_pipeline.py           # Point d'entrée Streamlit
├── requirements.txt
├── .env                            # Clés API (non versionné)
├── nachos.png                      # Logo sidebar
│
├── pipeline/
│   ├── pipeline.py                 # Orchestrateur PipelineAgentX
│   ├── config.py                   # Lecture variables d'environnement
│   │
│   ├── modules/
│   │   ├── chargement_dataset.py   # Chargement & normalisation
│   │   ├── declencheur.py          # Détection déclencheur (Gini)
│   │   ├── agent_viralite.py       # Scoring de viralité
│   │   ├── detection_communautes.py# Clustering Louvain
│   │   ├── agent_langage.py        # NLP, récits, RAG (TF-IDF + KMeans)
│   │   └── agent_proposition.py    # Synthèse & brouillon de réponse
│   │
│   └── ui/
│       ├── router.py               # Routage des vues cuisine
│       ├── navigation.py           # Sélecteur timeline
│       ├── view_utils.py           # Utilitaires, styles CSS, header
│       ├── react_components.py     # Composants React (iframe CDN)
│       ├── charts.py               # Graphiques Plotly
│       │
│       └── views/
│           ├── client/             # Vue synthèse exécutive
│           │   └── synthese_executive.py
│           └── cuisine/            # 11 écrans d'analyse agentique
```

---

## Stack technique

| Couche | Technologie |
|---|---|
| Interface | Streamlit ≥ 1.40 |
| Visualisation | Plotly |
| Composants UI | React 18 (UMD, via CDN) |
| NLP | TF-IDF, KMeans — scikit-learn 1.6.1 |
| Détection communautés | Louvain — NetworkX |
| Scoring viralité | ML — scikit-learn / joblib |
| Chat IA | Google Gemini 2.0 Flash (google-genai) |
| Données | pandas, openpyxl, pyarrow |
| Config | python-decouple (.env) |

---

## Équipe

Projet réalisé dans le cadre du **Datathon NEXA 2026** — IA School, Groupe PX8.
