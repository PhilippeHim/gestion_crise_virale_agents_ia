"""
crisis_agents (module unique) — Cellule de veille & réponse de crise informationnelle.
Colab : déposer ce fichier à la racine (/content) puis
    from crisis_agents import Orchestrateur, AgentVeille, AgentNarratif, AgentRedacteur, LLMClient
Pilotage par SchemaConfig (test Coca : rien de spécifique au cas codé en dur).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import os, re, collections
import numpy as np
import pandas as pd


# ======================================================================
# ---- config.py ----
# ======================================================================
@dataclass
class SchemaConfig:
    """Mapping rôle logique -> nom de colonne réel. Seul point d'adaptation à un nouveau corpus."""
    date: str = "Date"
    author: str = "Author"
    text: str = "message_normalizer"
    engagement: str = "Engagement Type"   # valeur retweet ci-dessous
    repost_of: str = "X Repost of"        # URL du post original retweeté
    reply_to: str = "X Reply to"
    mentions: str = "Mentioned Authors"
    hashtags: str = "Hashtags"
    sentiment: str = "Sentiment"          # libellés ci-dessous
    followers: str = "X Followers"
    verified: str = "X Verified"
    reach: str = "Reach"
    impressions: str = "Impressions"
    likes: str = "Likes"
    shares: str = "Shares"
    comments: str = "Comments"
    url: str = "Url"
    # valeurs (et non colonnes) propres au format d'export — paramétrables aussi
    retweet_value: str = "RETWEET"
    negative_label: str = "negative"


# --------------------------------------------------------------------------- #
# Primitives génériques (réutilisées par plusieurs agents)
# --------------------------------------------------------------------------- #
def extract_handle(url) -> str | None:
    """Handle de l'auteur original depuis une URL de post X/Twitter."""
    if pd.isna(url):
        return None
    m = re.search(r"twitter\.com/([^/]+)/status", str(url))
    return m.group(1).lower() if m else None


def extract_status_id(url) -> str | None:
    if pd.isna(url):
        return None
    m = re.search(r"status[es]*/(\d+)", str(url))
    return m.group(1) if m else None


def prepare(df: pd.DataFrame, cfg: SchemaConfig) -> pd.DataFrame:
    """Normalise un export brut : parse la date, dérive _source (auteur amplifié) et _is_original."""
    out = df.copy()
    out[cfg.date] = pd.to_datetime(out[cfg.date], errors="coerce")
    out["_source"] = out[cfg.repost_of].apply(extract_handle)
    out["_is_original"] = out[cfg.engagement].isna()
    return out


def robust_zscore(series: pd.Series, window: int = 7) -> pd.Series:
    """z-score robuste (médiane + MAD glissants, décalés d'un pas) — adapté au streaming/veille."""
    med = series.rolling(window, min_periods=2).median().shift(1)
    mad = (series.rolling(window, min_periods=2)
                 .apply(lambda x: np.median(np.abs(x - np.median(x))), raw=True).shift(1))
    scale = (1.4826 * mad).clip(lower=max(1.0, series.median() * 0.1))
    return (series - med) / scale


def gini(x) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return float("nan")
    c = np.cumsum(x)
    return float((n + 1 - 2 * np.sum(c) / c[-1]) / n)


# ======================================================================
# ---- llm.py ----
# ======================================================================
DEFAULTS = {
    "gemini":    "gemini-flash-latest",
    "mistral":   "mistral-small-latest",
    "anthropic": "claude-sonnet-4-6",
    "openai":    "gpt-4o-mini",
}


@dataclass
class LLMClient:
    provider: str = "gemini"     # <-- l'unique interrupteur de fournisseur
    model: str | None = None
    temperature: float = 0.2     # bas = sorties neutres et stables (posture du projet)

    def __post_init__(self):
        self.provider = self.provider.lower()
        self.model = self.model or DEFAULTS[self.provider]

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Renvoie le texte généré. Lève une exception claire si la clé/SDK manque."""
        return getattr(self, f"_{self.provider}")(prompt, system)

    # --- implémentations par fournisseur (imports paresseux) ---------------- #
    def _gemini(self, prompt, system):
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(self.model, system_instruction=system)
        r = model.generate_content(prompt, generation_config={"temperature": self.temperature})
        return r.text.strip()

    def _mistral(self, prompt, system):
        from mistralai import Mistral
        client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        r = client.chat.complete(model=self.model, messages=msgs, temperature=self.temperature)
        return r.choices[0].message.content.strip()

    def _anthropic(self, prompt, system):
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        r = client.messages.create(model=self.model, max_tokens=1024,
                                    system=system or "", temperature=self.temperature,
                                    messages=[{"role": "user", "content": prompt}])
        return r.content[0].text.strip()

    def _openai(self, prompt, system):
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        r = client.chat.completions.create(model=self.model, messages=msgs,
                                           temperature=self.temperature)
        return r.choices[0].message.content.strip()


# ======================================================================
# ---- network.py ----
# ======================================================================
import networkx as nx



def run_louvain(graph, weight="weight", seed=42):
    """Renvoie (part: dict noeud->communauté, modularité, backend)."""
    try:
        from networkx.algorithms.community import louvain_communities, modularity
        comms = louvain_communities(graph, weight=weight, seed=seed)
        part = {n: i for i, c in enumerate(comms) for n in c}
        return part, modularity(graph, comms, weight=weight), "networkx"
    except Exception:
        import community.community_louvain as cl
        from networkx.algorithms.community import modularity
        part = cl.best_partition(graph, weight=weight, random_state=seed)
        groups = {}
        for n, c in part.items():
            groups.setdefault(c, set()).add(n)
        return part, modularity(graph, list(groups.values()), weight=weight), "python-louvain"


def build_coamplification_graph(df, cfg: SchemaConfig, min_rt=10):
    """Graphe biparti pondéré retweeteur<->source (sources relayées >= min_rt fois)."""
    rt = df[(df[cfg.engagement] == cfg.retweet_value) & df["_source"].notna()]
    src_total = rt["_source"].value_counts()
    kept = set(src_total[src_total >= min_rt].index)
    edges = (rt[rt["_source"].isin(kept)]
             .groupby([cfg.author, "_source"]).size().reset_index(name="w"))
    G = nx.Graph()
    for _, r in edges.iterrows():
        G.add_edge(("u", r[cfg.author]), ("s", r["_source"]), weight=r["w"])
    if G.number_of_nodes() == 0:
        return G, src_total
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    return G, src_total


@dataclass
class Community:
    cid: int
    n_retweeters: int
    pivot_sources: list      # [(handle, rt_count), ...]
    pct_negative: float
    pct_verified: float
    peak_day: str
    volume: int


def detect_communities(df, cfg: SchemaConfig, min_rt=10, top_n=6, seed=42):
    """Détecte les communautés et les caractérise. Renvoie (communities, modularity, n_total, user_comm)."""
    G, src_total = build_coamplification_graph(df, cfg, min_rt)
    if G.number_of_nodes() == 0:
        return [], float("nan"), 0, {}
    part, mod, _ = run_louvain(G, seed=seed)
    user_comm = {n[1]: c for n, c in part.items() if n[0] == "u"}

    rt = df[df[cfg.engagement] == cfg.retweet_value].copy()
    rt = rt[rt[cfg.author].isin(user_comm)]
    rt["_comm"] = rt[cfg.author].map(user_comm)

    sizes = collections.Counter(user_comm.values())
    src_by_comm = collections.defaultdict(collections.Counter)
    for node, c in part.items():
        if node[0] == "s":
            src_by_comm[c][node[1]] = int(src_total.get(node[1], 0))

    out = []
    for cid, _ in sizes.most_common(top_n):
        sub = rt[rt["_comm"] == cid]
        daily = sub.set_index(cfg.date).resample("D").size()
        out.append(Community(
            cid=cid, n_retweeters=sizes[cid],
            pivot_sources=src_by_comm[cid].most_common(3),
            pct_negative=round((sub[cfg.sentiment] == cfg.negative_label).mean() * 100, 1),
            pct_verified=round(sub[cfg.verified].mean() * 100, 1),
            peak_day=f"{daily.idxmax():%Y-%m-%d}" if len(daily) else "n/a",
            volume=int(len(sub)),
        ))
    return out, round(mod, 3), len(set(part.values())), user_comm


# ======================================================================
# ---- rag.py ----
# ======================================================================
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity



def _clean(t):
    t = re.sub(r"http\S+|www\.\S+", " ", str(t))
    return re.sub(r"\s+", " ", t).strip()


class CorpusRetriever:
    """Index TF-IDF sur les textes uniques + volume amplifié (poids de représentativité)."""
    def __init__(self, cfg: SchemaConfig = SchemaConfig()):
        self.cfg = cfg
        self._fitted = False

    def fit(self, df: pd.DataFrame):
        cfg = self.cfg
        texts = df[cfg.text].dropna().astype(str).map(_clean)
        texts = texts[texts.str.len() > 3]
        self.volume_of = texts.value_counts()
        self.docs = texts.drop_duplicates().tolist()
        self.vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=3)
        self.M = self.vec.fit_transform(self.docs)
        self._fitted = True
        return self

    def query(self, text: str, top_k: int = 6, min_sim: float = 0.05):
        """Renvoie [(message, volume, similarité)] les plus proches, pondérés par représentativité."""
        assert self._fitted, "Appeler .fit(df) d'abord"
        q = self.vec.transform([_clean(text)])
        sims = cosine_similarity(q, self.M).ravel()
        # score = similarité * log(1+volume) : on privilégie le proche ET le très repartagé
        vols = np.array([self.volume_of[d] for d in self.docs])
        score = sims * np.log1p(vols)
        order = score.argsort()[::-1]
        out = []
        for i in order:
            if sims[i] < min_sim:
                break
            out.append((self.docs[i], int(vols[i]), round(float(sims[i]), 3)))
            if len(out) >= top_k:
                break
        return out


# ======================================================================
# ---- veille.py ----
# ======================================================================
@dataclass
class VeilleResult:
    peaks: pd.DataFrame                 # date | volume | zscore
    trigger: dict                       # déclencheur retenu + métriques + reprise directe
    trigger_candidates: pd.DataFrame    # top posts originaux pré-pic (traçabilité)
    amplifiers: pd.DataFrame            # source | retweets | part_%
    concentration: dict                 # gini_contenu, gini_relais, top_k_share
    brief: str                          # synthèse lisible (jury / cellule de crise)

    def __repr__(self):
        return self.brief


class AgentVeille:
    def __init__(self, cfg: SchemaConfig = SchemaConfig(),
                 z_threshold: float = 3.0, freq: str = "D",
                 baseline_window: int = 7, top_amplifiers: int = 10):
        self.cfg = cfg
        self.z_threshold = z_threshold
        self.freq = freq
        self.baseline_window = baseline_window
        self.top_amplifiers = top_amplifiers

    # -- briques internes -------------------------------------------------- #
    def _detect_peaks(self, df) -> pd.DataFrame:
        cfg = self.cfg
        vol = df.set_index(cfg.date).resample(self.freq).size()
        z = robust_zscore(vol, self.baseline_window)
        peaks = (pd.DataFrame({"volume": vol, "zscore": z})
                 .dropna().query("zscore > @self.z_threshold")
                 .sort_values("zscore", ascending=False))
        peaks.index.name = "date"
        return peaks.reset_index()

    def _find_trigger(self, df, first_peak_ts, institutional_account):
        cfg = self.cfg
        pre = df[(df["_is_original"]) &
                 (df[cfg.date] <= first_peak_ts + pd.Timedelta(days=1))]
        candidates = (pre.sort_values(cfg.reach, ascending=False)
                      [[cfg.date, cfg.author, cfg.reach, cfg.impressions, cfg.likes, cfg.shares]]
                      .head(5).reset_index(drop=True))

        # si un compte institutionnel est fourni, on privilégie SON post pré-pic le plus fort
        chosen = None
        if institutional_account:
            inst = pre[pre[cfg.author].astype(str).str.lower() == institutional_account.lower()]
            if len(inst):
                chosen = inst.sort_values(cfg.reach, ascending=False).iloc[0]
        if chosen is None and len(candidates):
            chosen = pre.sort_values(cfg.reach, ascending=False).iloc[0]

        trigger = {}
        if chosen is not None:
            sid = extract_status_id(chosen[cfg.url])
            reposts = int(df[cfg.repost_of].astype(str).str.contains(str(sid), na=False).sum()) if sid else None
            replies = int(df[cfg.reply_to].astype(str).str.contains(str(sid), na=False).sum()) if sid else None
            trigger = {
                "author": chosen[cfg.author], "date": chosen[cfg.date],
                "reach": int(chosen[cfg.reach]), "impressions": int(chosen[cfg.impressions]),
                "likes": int(chosen[cfg.likes]), "shares": int(chosen[cfg.shares]),
                "direct_reposts": reposts, "direct_replies": replies,
            }
        return trigger, candidates

    def _amplifiers(self, df):
        cfg = self.cfg
        src = df["_source"].value_counts()
        rtr = df[df[cfg.engagement] == cfg.retweet_value][cfg.author].value_counts()
        top = (src.head(self.top_amplifiers).rename("retweets").to_frame()
               .assign(part_pct=lambda d: (d["retweets"] / src.sum() * 100).round(1)))
        top.index.name = "source"
        conc = {
            "gini_contenu": round(gini(src.values), 3),
            "gini_relais": round(gini(rtr.values), 3),
            "n_sources": int(len(src)), "n_relais": int(len(rtr)),
            "top20_share_pct": round(src.head(20).sum() / src.sum() * 100, 1),
        }
        return top.reset_index(), conc

    # -- API publique ------------------------------------------------------ #
    def run(self, df_raw: pd.DataFrame, institutional_account: Optional[str] = None) -> VeilleResult:
        cfg = self.cfg
        df = prepare(df_raw, cfg)

        peaks = self._detect_peaks(df)
        first_peak_ts = peaks["date"].min() if len(peaks) else df[cfg.date].max()
        trigger, candidates = self._find_trigger(df, first_peak_ts, institutional_account)
        amplifiers, concentration = self._amplifiers(df)

        brief = self._brief(df, peaks, trigger, amplifiers, concentration)
        return VeilleResult(peaks, trigger, candidates, amplifiers, concentration, brief)

    def _brief(self, df, peaks, trigger, amplifiers, conc) -> str:
        cfg = self.cfg
        n = len(df)
        lines = ["=== AGENT VEILLE — synthèse ===",
                 f"Corpus : {n:,} messages | {df[cfg.date].min():%Y-%m-%d} -> {df[cfg.date].max():%Y-%m-%d}"]
        if len(peaks):
            top_peaks = ", ".join(f"{r['date']:%d/%m} (z={r['zscore']:.0f})"
                                  for _, r in peaks.head(4).iterrows())
            lines.append(f"Pics détectés ({len(peaks)}) : {top_peaks}")
        if trigger:
            tr = trigger
            dr = tr.get("direct_reposts")
            share = f" = {dr/n*100:.1f}% de la crise" if dr else ""
            lines.append(f"Déclencheur : @{tr['author']} le {tr['date']:%d/%m %H:%M} "
                         f"(reach {tr['reach']:,}); reprise directe {dr} RT{share}")
            lines.append("  -> la portée vient des amplificateurs, pas du seul compte source.")
        amp = ", ".join(f"@{r['source']} ({r['retweets']})" for _, r in amplifiers.head(5).iterrows())
        lines.append(f"Amplificateurs clés : {amp}")
        lines.append(f"Concentration : Gini contenu {conc['gini_contenu']} "
                     f"(top20 = {conc['top20_share_pct']}% des RT) | Gini relais {conc['gini_relais']}")
        return "\n".join(lines)


# ======================================================================
# ---- narratif.py ----
# ======================================================================
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


FR_STOP = ("le la les un une des de du d l et en a au aux ce que qui pour pas plus sur se sa son "
           "ses ne rt c est il elle on nous vous ils elles je tu me te y dans par avec sans mais "
           "ou donc or ni car cette cet ces leur leurs vos nos mon ma mes ton ta tes notre votre "
           "qu n s t si sont ont ca fait tout comme meme bien etre cela faire dit").split()


def _clean(t):
    t = re.sub(r"http\S+|www\.\S+", " ", str(t))
    return re.sub(r"\s+", " ", t).strip()


@dataclass
class Narrative:
    nid: int
    terms: list
    example: str
    unique_texts: int
    volume: int           # volume amplifié (RT inclus)
    pct_negative: float
    risk_score: float     # 0-100, déterministe
    risk_band: str        # faible / moyen / élevé
    name: str = ""        # rempli par LLM ou fallback mots-clés
    risk_rationale: str = ""


@dataclass
class NarratifResult:
    narratives: list
    communities: list
    modularity: float
    n_communities: int
    silhouette: float
    method: str
    k: int
    brief: str
    def __repr__(self): return self.brief


class AgentNarratif:
    def __init__(self, cfg: SchemaConfig = SchemaConfig(), llm: Optional[LLMClient] = None,
                 method: str = "tfidf", k: int = 6, emb_model="paraphrase-multilingual-MiniLM-L12-v2",
                 w_volume: float = 0.6, w_negativity: float = 0.4, seed: int = 42):
        self.cfg, self.llm, self.method, self.k = cfg, llm, method, k
        self.emb_model = emb_model
        self.w_volume, self.w_negativity, self.seed = w_volume, w_negativity, seed

    # -- vectorisation pilotée par METHODE --------------------------------- #
    def _vectorize(self, texts):
        if self.method == "tfidf":
            vec = TfidfVectorizer(max_features=3000, ngram_range=(1, 2), min_df=5,
                                  max_df=0.25, stop_words=FR_STOP)
            return vec.fit_transform(texts)
        elif self.method == "embeddings":
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self.emb_model)
            return model.encode(texts, batch_size=64, normalize_embeddings=True,
                                show_progress_bar=False)
        raise ValueError("method doit etre 'tfidf' ou 'embeddings'")

    @staticmethod
    def _describe(texts, labels, topn=7):
        tv = TfidfVectorizer(max_features=3000, ngram_range=(1, 2), min_df=5,
                             max_df=0.25, stop_words=FR_STOP)
        M = tv.fit_transform(texts); terms = np.array(tv.get_feature_names_out())
        out = {}
        for ci in sorted(set(labels)):
            centroid = np.asarray(M[labels == ci].mean(axis=0)).ravel()
            out[ci] = list(terms[centroid.argsort()[::-1][:topn]])
        return out

    # -- nommage + justification (LLM optionnel) --------------------------- #
    def _name_with_llm(self, terms, example):
        prompt = (f"Mots-clés d'un récit dans une polémique en ligne : {', '.join(terms)}.\n"
                  f"Exemple de message : « {example[:200]} ».\n"
                  "Donne UNIQUEMENT un titre neutre et descriptif de 3 à 6 mots pour ce récit, "
                  "sans prise de position, sans guillemets.")
        return self.llm.complete(prompt, system="Tu es analyste de crise. Ton strictement neutre, "
                                                 "factuel, sans jugement politique.").splitlines()[0].strip()

    def _risk_rationale_with_llm(self, name, vol_share, neg, band):
        prompt = (f"Récit « {name} » : {vol_share:.0%} du volume de la crise, {neg:.0f}% de messages "
                  f"négatifs, risque {band}. En UNE phrase neutre, explique pourquoi ce niveau de "
                  "risque pour une cellule de communication.")
        return self.llm.complete(prompt, system="Analyste de crise, neutre et concis.")

    # -- API publique ------------------------------------------------------ #
    def run(self, df_raw: pd.DataFrame) -> NarratifResult:
        cfg = self.cfg
        df = prepare(df_raw, cfg)

        # 1) Récits : dédoublonnage sur textes uniques
        texts = df[cfg.text].dropna().astype(str).map(_clean)
        texts = texts[texts.str.len() > 3]
        volume_of = texts.value_counts()
        sentiment_of = (df.dropna(subset=[cfg.text])
                        .assign(_c=lambda d: d[cfg.text].astype(str).map(_clean))
                        .groupby("_c")[cfg.sentiment]
                        .apply(lambda s: (s == cfg.negative_label).mean()))
        unique_texts = texts.drop_duplicates().tolist()

        X = self._vectorize(unique_texts)
        labels = KMeans(n_clusters=self.k, random_state=self.seed, n_init=10).fit_predict(X)
        try:
            from sklearn.metrics import silhouette_score
            sil = round(float(silhouette_score(X, labels, sample_size=min(3000, len(labels)),
                                                random_state=self.seed)), 3)
        except Exception:
            sil = float("nan")
        desc = self._describe(unique_texts, labels)

        # volume + négativité par récit
        raw = []
        for ci in sorted(set(labels)):
            cl = [unique_texts[i] for i in range(len(unique_texts)) if labels[i] == ci]
            vol = int(volume_of[cl].sum())
            neg = float(np.mean([sentiment_of.get(t, 0.0) for t in cl]) * 100)
            example = max(cl, key=lambda t: volume_of[t])
            raw.append((int(ci), desc[ci], example, len(cl), vol, neg))

        total_vol = sum(r[4] for r in raw)
        max_share = max(r[4] for r in raw) / total_vol

        narratives = []
        for ci, terms, example, n_uni, vol, neg in raw:
            vol_share = vol / total_vol
            score = 100 * (self.w_volume * (vol_share / max_share) + self.w_negativity * (neg / 100))
            band = "élevé" if score >= 60 else "moyen" if score >= 35 else "faible"
            name = ", ".join(terms[:3])           # fallback déterministe
            rationale = ""
            if self.llm is not None:
                try:
                    name = self._name_with_llm(terms, example)
                    rationale = self._risk_rationale_with_llm(name, vol_share, neg, band)
                except Exception as e:
                    rationale = f"(LLM indisponible : {type(e).__name__})"
            narratives.append(Narrative(ci, terms, example[:120], n_uni, vol, round(neg, 1),
                                        round(score, 1), band, name, rationale))
        narratives.sort(key=lambda x: x.risk_score, reverse=True)

        # 2) Communautés
        communities, mod, n_comm, _ = detect_communities(df, cfg, top_n=6, seed=self.seed)

        brief = self._brief(narratives, communities, mod, n_comm, sil)
        return NarratifResult(narratives, communities, mod, n_comm, sil, self.method, self.k, brief)

    def _brief(self, narratives, communities, mod, n_comm, sil):
        L = ["=== AGENT NARRATIF — synthèse ===",
             f"Méthode={self.method} | k={self.k} | silhouette={sil} (clustering exploratoire)",
             f"Communautés d'amplification : {n_comm} (modularité {mod})", "", "Récits (par risque) :"]
        for r in narratives:
            L.append(f"  [{r.risk_band:6s} {r.risk_score:4.0f}] {r.name}  "
                     f"— vol {r.volume:,}, {r.pct_negative:.0f}% nég.")
        return "\n".join(L)


# ======================================================================
# ---- redacteur.py ----
# ======================================================================
SYSTEM = ("Tu es un rédacteur d'une cellule de communication de crise. Tu écris des réponses "
          "institutionnelles strictement NEUTRES et factuelles. Interdits : prise de position "
          "politique, attaque, ironie, promesse non vérifiable, chiffre non fourni. Tu réponds "
          "uniquement aux préoccupations explicitement présentes dans les messages fournis.")


@dataclass
class DraftResponse:
    nid: int
    narrative_name: str
    evidence: list                 # [(message_réel, volume, similarité)]
    draft: str
    prompt: str = ""               # ce qui a été envoyé au LLM (traçabilité jury)
    needs_human_validation: bool = True


class AgentRedacteur:
    def __init__(self, cfg: SchemaConfig = SchemaConfig(), llm: Optional[LLMClient] = None,
                 retriever: Optional[CorpusRetriever] = None, organization: Optional[str] = None,
                 top_k: int = 6):
        self.cfg = cfg
        self.llm = llm
        self.retriever = retriever
        self.org = organization or "[Organisation]"
        self.top_k = top_k

    def _build_prompt(self, narrative_name, evidence):
        bullet = "\n".join(f"- « {m[:200]} »" for m, _, _ in evidence)
        return (f"Récit à traiter : {narrative_name}\n\n"
                f"Messages réels représentatifs de ce récit (issus du corpus) :\n{bullet}\n\n"
                f"Rédige, au nom de {self.org}, une réponse publique de 4 à 6 phrases qui :\n"
                "1) accuse réception de la préoccupation exprimée, sans la déformer ;\n"
                "2) apporte un élément factuel de clarification OU annonce une démarche concrète ;\n"
                "3) reste strictement neutre et apaisée, sans contre-attaque.\n"
                "N'invente aucun chiffre ni fait absent des messages ci-dessus.")

    def _draft_one(self, narrative_name, evidence):
        prompt = self._build_prompt(narrative_name, evidence)
        if self.llm is None:
            draft = ("[BROUILLON non généré — aucun LLM fourni]\n"
                     "Fournir llm=LLMClient(\"gemini\") pour générer. "
                     "Le contexte RAG ci-dessus est prêt à être envoyé.")
        else:
            try:
                draft = self.llm.complete(prompt, system=SYSTEM)
            except Exception as e:
                draft = f"[Échec génération LLM : {type(e).__name__}: {e}]"
        return prompt, draft

    def run(self, df_raw: pd.DataFrame, narratives, targets: Optional[list] = None):
        """narratives : liste d'objets Narrative (de l'Agent Narratif). targets : ids à traiter (def. tous)."""
        df = prepare(df_raw, self.cfg)
        if self.retriever is None:
            self.retriever = CorpusRetriever(self.cfg).fit(df)

        responses = []
        for nar in narratives:
            if targets is not None and nar.nid not in targets:
                continue
            # requête RAG : on ancre sur les termes + l'exemple du récit
            query = f"{nar.name}. {' '.join(nar.terms)}. {nar.example}"
            evidence = self.retriever.query(query, top_k=self.top_k)
            prompt, draft = self._draft_one(nar.name, evidence)
            responses.append(DraftResponse(nar.nid, nar.name, evidence, draft, prompt))
        return responses


# ======================================================================
# ---- orchestrateur.py ----
# ======================================================================
@dataclass
class CrisisReport:
    veille: VeilleResult
    narratif: NarratifResult
    responses: list           # DraftResponse (brouillons à valider)
    brief: str
    def __repr__(self): return self.brief


class Orchestrateur:
    def __init__(self, cfg: SchemaConfig = SchemaConfig(), llm: Optional[LLMClient] = None,
                 method: str = "tfidf", k: int = 6, draft_top_n: int = 3):
        self.cfg, self.llm, self.method, self.k = cfg, llm, method, k
        self.draft_top_n = draft_top_n   # nb de récits (par risque) pour lesquels on rédige

    def run(self, df: pd.DataFrame, institutional_account: Optional[str] = None,
            organization: Optional[str] = None, targets: Optional[list] = None) -> CrisisReport:
        # 1) Veille
        veille = AgentVeille(self.cfg).run(df, institutional_account=institutional_account)
        # 2) Narratif
        narratif = AgentNarratif(self.cfg, llm=self.llm, method=self.method, k=self.k).run(df)
        # 3) Rédacteur — priorisation par risque (sauf cibles imposées)
        if targets is None:
            targets = [int(n.nid) for n in narratif.narratives[:self.draft_top_n]]  # déjà triés par risque
        responses = AgentRedacteur(self.cfg, llm=self.llm, organization=organization)\
                        .run(df, narratif.narratives, targets=targets)

        return CrisisReport(veille, narratif, responses, self._brief(veille, narratif, responses, targets))

    def _brief(self, veille, narratif, responses, targets):
        L = ["#" * 60, "# RAPPORT DE CRISE — pipeline Veille → Narratif → Rédacteur", "#" * 60, ""]
        L.append(veille.brief); L.append("")
        L.append(narratif.brief); L.append("")
        L.append(f"=== AGENT RÉDACTEUR — {len(responses)} brouillon(s) (récits prioritaires {targets}) ===")
        for r in responses:
            preview = r.draft.replace("\n", " ")[:90]
            L.append(f"  • {r.narrative_name} : {preview}…")
        L.append("")
        L.append(">>> ÉTAPE SUIVANTE : VALIDATION HUMAINE obligatoire avant toute diffusion. <<<")
        return "\n".join(L)
