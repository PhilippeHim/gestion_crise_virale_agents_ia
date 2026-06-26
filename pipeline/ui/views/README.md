# Découpage des vues Streamlit PX8

Chaque écran cliquable de la timeline cuisine correspond à un fichier dans `pipeline/ui/views/cuisine/`.
Chaque bloc de la synthèse client correspond à un fichier dans `pipeline/ui/views/client/`.

## Règles de contribution

- Garder la signature `afficher(donnees: dict) -> None`.
- Ne pas renommer les clés de timeline sans modifier `pipeline/ui/router.py` et `pipeline/ui/navigation.py`.
- Lire les données via le dictionnaire `donnees`, sans modifier les sorties des agents depuis une vue.
- Mettre les graphes partagés dans `pipeline/ui/charts.py`.
- Mettre les composants communs, contrats et helpers dans `pipeline/ui/view_utils.py`.
- Éviter les imports depuis `streamlit_pipeline.py` : ce fichier est seulement le point d'entrée.

## Fichiers centraux

- `streamlit_pipeline.py` : démarre l'application.
- `pipeline/ui/router.py` : associe une clé de badge à un fichier de vue.
- `pipeline/ui/navigation.py` : construit les badges des deux timelines.
- `pipeline/ui/view_utils.py` : style, contrats, formatage, état Streamlit.
- `pipeline/ui/charts.py` : graphiques Plotly réutilisables.
