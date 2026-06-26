import pandas as pd
import plotly.express as px

from pipeline.ui.view_utils import valeur_tableau_lisible

def graphique_volume_journalier(donnees: dict):
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Date" not in dataset.columns:
        return None

    base = dataset.copy()
    base["Date"] = pd.to_datetime(base["Date"], errors="coerce")
    base = base.dropna(subset=["Date"])
    if base.empty:
        return None

    quotidien = base.set_index("Date").resample("D").size().reset_index(name="messages")
    fig = px.area(
        quotidien,
        x="Date",
        y="messages",
        title="Volume quotidien de messages",
    )
    fig.update_traces(line_color="#4b2e83", fillcolor="rgba(75, 46, 131, 0.22)")
    fig.update_layout(
        height=250,
        margin=dict(l=8, r=8, t=38, b=8),
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Messages",
    )
    return fig


def graphique_top_auteurs(donnees: dict):
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Author" not in dataset.columns:
        return None

    top = dataset["Author"].fillna("inconnu").value_counts().head(15).reset_index()
    top.columns = ["Auteur", "Messages"]
    fig = px.bar(
        top.sort_values("Messages"),
        x="Messages",
        y="Auteur",
        orientation="h",
        title="Auteurs les plus actifs",
        color="Messages",
        color_continuous_scale=["#7db7b2", "#4b2e83"],
    )
    fig.update_layout(height=360, margin=dict(l=8, r=8, t=38, b=8), yaxis_title=None)
    return fig


def graphique_types_engagement(donnees: dict):
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Engagement Type" not in dataset.columns:
        return None

    repartition = dataset["Engagement Type"].fillna("ORIGINAL").value_counts().reset_index()
    repartition.columns = ["Type", "Messages"]
    fig = px.pie(
        repartition,
        names="Type",
        values="Messages",
        title="Nature des messages",
        hole=0.45,
        color_discrete_sequence=["#4b2e83", "#ff7a33", "#7db7b2", "#6b7280"],
    )
    fig.update_layout(height=330, margin=dict(l=8, r=8, t=38, b=8))
    return fig


def graphique_sentiment_journalier(donnees: dict):
    dataset = donnees.get("dataset")
    if (
        not isinstance(dataset, pd.DataFrame)
        or dataset.empty
        or "Date" not in dataset.columns
        or "Sentiment" not in dataset.columns
    ):
        return None

    base = dataset.copy()
    base["Date"] = pd.to_datetime(base["Date"], errors="coerce").dt.date
    base = base.dropna(subset=["Date"])
    if base.empty:
        return None

    quotidien = base.groupby(["Date", "Sentiment"]).size().reset_index(name="Messages")
    fig = px.area(
        quotidien,
        x="Date",
        y="Messages",
        color="Sentiment",
        title="Tonalité au fil du temps",
        color_discrete_map={"negative": "#ff7a33", "neutral": "#4b2e83", "positive": "#7db7b2"},
    )
    fig.update_layout(height=330, margin=dict(l=8, r=8, t=38, b=8), xaxis_title=None)
    return fig


def graphique_viralite_distribution(donnees: dict):
    dataset = donnees.get("dataset")
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or "Classe_viralite" not in dataset.columns:
        return None

    repartition = dataset["Classe_viralite"].fillna("Non classé").value_counts().reset_index()
    repartition.columns = ["Classe", "Messages"]
    fig = px.bar(
        repartition,
        x="Classe",
        y="Messages",
        title="Répartition des classes de viralité",
        color="Classe",
        color_discrete_sequence=["#4b2e83", "#7db7b2", "#ff7a33"],
    )
    fig.update_layout(height=320, margin=dict(l=8, r=8, t=38, b=8), showlegend=False)
    return fig


def graphique_viralite_reach(donnees: dict):
    dataset = donnees.get("dataset")
    colonnes = {"Viralite", "Reach", "X Followers", "Classe_viralite"}
    if not isinstance(dataset, pd.DataFrame) or dataset.empty or not colonnes.issubset(dataset.columns):
        return None

    base = dataset[list(colonnes)].dropna().copy()
    if base.empty:
        return None
    base = base.sort_values("Reach", ascending=False).head(1200)
    fig = px.scatter(
        base,
        x="X Followers",
        y="Reach",
        color="Classe_viralite",
        size="Viralite",
        title="Audience potentielle vs score de viralité",
        color_discrete_map={
            "Non Viral": "#7db7b2",
            "Moyennement Viral": "#4b2e83",
            "Viral": "#ff7a33",
        },
    )
    fig.update_layout(height=360, margin=dict(l=8, r=8, t=38, b=8))
    return fig


def graphique_communautes_risque(donnees: dict):
    table = dataframe_communautes(donnees)
    colonnes = {"nombre_messages", "pct_negative", "nombre_retweeteurs", "pct_verified"}
    if table.empty or not colonnes.issubset(table.columns):
        return None

    fig = px.scatter(
        table,
        x="nombre_messages",
        y="pct_negative",
        size="nombre_retweeteurs",
        color="pct_verified",
        hover_name="id",
        hover_data=["jour_pic", "sources_lisibles"],
        title="Communautés : volume, négativité et comptes vérifiés",
        color_continuous_scale=["#7db7b2", "#ff7a33"],
    )
    fig.update_layout(
        height=380,
        margin=dict(l=8, r=8, t=38, b=8),
        xaxis_title="Messages retweetés",
        yaxis_title="% négatif",
        coloraxis_colorbar_title="% vérifiés",
    )
    return fig


def graphique_sources_pivots(donnees: dict):
    lignes = []
    for communaute in donnees.get("communautes", []):
        for source, volume in communaute.get("sources_pivots", []):
            lignes.append({"Source": source, "Retweets": volume, "Communauté": str(communaute.get("id"))})
    if not lignes:
        return None

    table = pd.DataFrame(lignes).sort_values("Retweets", ascending=False).head(15)
    fig = px.bar(
        table.sort_values("Retweets"),
        x="Retweets",
        y="Source",
        color="Communauté",
        orientation="h",
        title="Sources pivots amplifiées par les communautés",
        color_discrete_sequence=["#4b2e83", "#ff7a33", "#7db7b2", "#6b7280"],
    )
    fig.update_layout(height=380, margin=dict(l=8, r=8, t=38, b=8), yaxis_title=None)
    return fig


def graphique_recits(donnees: dict):
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
    if not recits:
        return None

    df = pd.DataFrame(recits).head(6)
    if df.empty or not {"nom", "volume", "pct_negative"}.issubset(df.columns):
        return None

    fig = px.bar(
        df.sort_values("volume"),
        x="volume",
        y="nom",
        orientation="h",
        color="pct_negative",
        color_continuous_scale=["#4b2e83", "#ff7a33"],
        title="Récits prioritaires : volume et négativité",
    )
    fig.update_layout(
        height=280,
        margin=dict(l=8, r=8, t=38, b=8),
        xaxis_title="Volume",
        yaxis_title=None,
        coloraxis_colorbar_title="% nég.",
    )
    return fig


def graphique_recits_risque(donnees: dict):
    narratif = donnees.get("narratif", {})
    recits = narratif.get("recits", []) if isinstance(narratif, dict) else []
    if not recits:
        return None

    df = pd.DataFrame(recits)
    colonnes = {"nom", "volume", "pct_negative", "score_risque", "niveau_risque"}
    if df.empty or not colonnes.issubset(df.columns):
        return None

    fig = px.scatter(
        df,
        x="volume",
        y="pct_negative",
        size="score_risque",
        color="niveau_risque",
        hover_name="nom",
        title="Carte des récits : visibilité vs agressivité",
        color_discrete_map={"faible": "#7db7b2", "moyen": "#4b2e83", "eleve": "#ff7a33"},
    )
    fig.update_layout(
        height=380,
        margin=dict(l=8, r=8, t=38, b=8),
        xaxis_title="Volume de messages",
        yaxis_title="% négatif",
    )
    return fig


def graphique_corpus_doublons(donnees: dict):
    narratif = donnees.get("narratif", {})
    corpus = narratif.get("corpus", {}) if isinstance(narratif, dict) else {}
    if not corpus:
        return None

    table = pd.DataFrame(
        [
            {"Étape": "Corpus reçu", "Messages": corpus.get("messages_total", 0)},
            {"Étape": "Textes uniques analysés", "Messages": corpus.get("messages_analyses", 0)},
            {"Étape": "Doublons ignorés pour le NLP", "Messages": corpus.get("messages_ignores_car_doublons", 0)},
        ]
    )
    fig = px.bar(
        table,
        x="Étape",
        y="Messages",
        title="Ce que l'agent NLP garde pour comprendre les récits",
        color="Étape",
        color_discrete_sequence=["#4b2e83", "#7db7b2", "#ff7a33"],
    )
    fig.update_layout(height=320, margin=dict(l=8, r=8, t=38, b=8), showlegend=False)
    return fig


def graphique_sentiment_global(donnees: dict):
    tonalite = donnees.get("narratif", {}).get("tonalite", {})
    repartition = tonalite.get("repartition", {}) if isinstance(tonalite, dict) else {}
    if not repartition:
        return None

    table = pd.DataFrame({"Sentiment": list(repartition.keys()), "Messages": list(repartition.values())})
    fig = px.pie(
        table,
        names="Sentiment",
        values="Messages",
        title="Répartition globale des sentiments",
        hole=0.45,
        color="Sentiment",
        color_discrete_map={"negative": "#ff7a33", "neutral": "#4b2e83", "positive": "#7db7b2"},
    )
    fig.update_layout(height=330, margin=dict(l=8, r=8, t=38, b=8))
    return fig


def dataframe_communautes(donnees: dict) -> pd.DataFrame:
    communautes = donnees.get("communautes", [])
    if not communautes:
        return pd.DataFrame()
    table = pd.DataFrame(communautes).drop(columns=["narratif"], errors="ignore")
    if "sources_pivots" in table.columns:
        table["sources_lisibles"] = table["sources_pivots"].map(valeur_tableau_lisible)
    return table
