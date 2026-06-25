"""
Démo Streamlit — Cellule de veille & réponse de crise informationnelle
======================================================================
Interface interactive (Plotly) pilotant les 3 agents + validation humaine.
Lancement :  streamlit run app.py   (crisis_agents.py dans le même dossier)
"""
import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from crisis_agents import Orchestrateur, LLMClient, SchemaConfig, prepare

st.set_page_config(page_title="Veille de crise", page_icon="🛰️", layout="wide")

# --------------------------------------------------------------------------- #
# Style
# --------------------------------------------------------------------------- #
st.markdown("""
<style>
  .block-container {padding-top: 2rem;}
  .risk-badge {padding:2px 10px;border-radius:12px;color:#fff;font-weight:600;font-size:.8rem;}
  .r-eleve{background:#c0392b;} .r-moyen{background:#e67e22;} .r-faible{background:#27ae60;}
  div[data-testid="stMetric"]{background:#f7f8fa;border:1px solid #eee;border-radius:12px;padding:12px 16px;}
  .stTabs [data-baseweb="tab"]{font-size:1rem;font-weight:600;}
</style>
""", unsafe_allow_html=True)

st.title("🛰️ Cellule de veille & réponse de crise")
st.caption("Pipeline générique Veille → Narratif → Rédacteur · validation humaine avant diffusion")

PALETTE = px.colors.qualitative.Set2
BAND_COLOR = {"élevé": "#c0392b", "moyen": "#e67e22", "faible": "#27ae60"}

# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("⚙️ Configuration")
    up = st.file_uploader("Corpus (.xlsx)", type=["xlsx"])
    method = st.selectbox("Vectorisation des récits", ["tfidf", "embeddings"])
    k = st.slider("Nombre de récits (k)", 3, 10, 6)
    draft_top_n = st.slider("Récits à traiter (par risque)", 1, 6, 3)
    inst = st.text_input("Compte institutionnel (optionnel)")
    org = st.text_input("Organisation qui répond", value="[Organisation]")
    st.divider()
    st.subheader("LLM (récits nommés + réponses)")
    provider = st.selectbox("Fournisseur", ["(aucun)", "gemini", "mistral", "anthropic", "openai"])
    api_key = st.text_input("Clé API", type="password")
    model = st.text_input("Modèle (optionnel)",
                          help="Vide = défaut du fournisseur. Ex Gemini : gemini-flash-latest, gemini-2.5-flash")
    run = st.button("🚀 Lancer l'analyse", type="primary", use_container_width=True)


@st.cache_data(show_spinner=False)
def load(file):
    return pd.read_excel(file)


def make_llm():
    if provider == "(aucun)" or not api_key:
        return None
    os.environ[f"{provider.upper()}_API_KEY"] = api_key
    return LLMClient(provider, model=(model or None))


# --------------------------------------------------------------------------- #
# Figures (testables hors Streamlit)
# --------------------------------------------------------------------------- #
def fig_volume(df, cfg, peaks, trigger):
    daily = prepare(df, cfg).set_index(cfg.date).resample("D").size()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily.index, y=daily.values, fill="tozeroy",
                             line=dict(color="#c0392b", width=2), name="messages/j"))
    if peaks is not None and len(peaks):
        pk = peaks.set_index("date").reindex(daily.index).dropna()
        fig.add_trace(go.Scatter(x=pk.index, y=daily.reindex(pk.index).values, mode="markers",
                                 marker=dict(color="#2c3e50", size=9, symbol="diamond"), name="pic"))
    if trigger:
        fig.add_vline(x=pd.Timestamp(trigger["date"]), line_dash="dash", line_color="#2c3e50")
        fig.add_annotation(x=pd.Timestamp(trigger["date"]), y=daily.max(),
                           text=f"Déclencheur @{trigger['author']}", showarrow=True, arrowhead=2)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10),
                      yaxis_title="messages / jour", showlegend=False)
    return fig


def fig_amplifiers(amp):
    a = amp.head(10).iloc[::-1]
    fig = px.bar(a, x="retweets", y="source", orientation="h", color="retweets",
                 color_continuous_scale="Reds", text="retweets")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10),
                      coloraxis_showscale=False, yaxis_title="", xaxis_title="retweets reçus")
    return fig


def fig_narratives(narratives):
    d = pd.DataFrame([{"récit": n.name[:38], "volume": n.volume, "niveau": n.risk_band,
                       "risque": n.risk_score, "% négatif": n.pct_negative} for n in narratives])
    d = d.iloc[::-1]
    fig = px.bar(d, x="volume", y="récit", orientation="h", color="niveau",
                 color_discrete_map=BAND_COLOR, text="volume",
                 hover_data=["risque", "% négatif"])
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="",
                      xaxis_title="volume amplifié (RT inclus)", legend_title="risque")
    return fig


def fig_communities(communities):
    d = pd.DataFrame([{"communauté": f"C{c.cid}", "pic": c.peak_day, "% négatif": c.pct_negative,
                       "retweeteurs": c.n_retweeters, "% vérifié": c.pct_verified,
                       "sources": ", ".join(f"@{h}" for h, _ in c.pivot_sources)} for c in communities])
    fig = px.scatter(d, x="pic", y="% négatif", size="retweeteurs", color="% négatif",
                     color_continuous_scale="RdYlGn_r", hover_name="communauté",
                     hover_data=["retweeteurs", "% vérifié", "sources"], size_max=55)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis_title="jour de pic", yaxis_title="% messages négatifs")
    return fig


# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #
if run and up is None:
    st.error("Charge d'abord un fichier .xlsx.")
if run and up is not None:
    df = load(up)
    with st.spinner("Pipeline en cours…"):
        report = Orchestrateur(method=method, k=k, llm=make_llm(), draft_top_n=draft_top_n).run(
            df, institutional_account=(inst or None), organization=org)
    st.session_state.update(report=report, df=df)

if "report" not in st.session_state:
    st.info("⬅️ Charge un corpus .xlsx et clique sur **Lancer l'analyse**.")
    st.stop()

report, df, cfg = st.session_state["report"], st.session_state["df"], SchemaConfig()
v, n = report.veille, report.narratif

# --- En-tête : cartes de synthèse ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Messages", f"{len(df):,}")
c2.metric("Pics détectés", len(v.peaks))
if v.trigger:
    c3.metric("Déclencheur", f"@{v.trigger['author']}", f"{v.trigger.get('direct_reposts','—')} RT directs")
c4.metric("Communautés", n.n_communities, f"modularité {n.modularity}")

tab1, tab2, tab3 = st.tabs(["🛰️ Veille", "🧩 Récits & communautés", "✍️ Réponses (à valider)"])

with tab1:
    st.subheader("Volume quotidien & pics")
    st.plotly_chart(fig_volume(df, cfg, v.peaks, v.trigger), use_container_width=True)
    cc1, cc2 = st.columns([3, 2])
    with cc1:
        st.subheader("Amplificateurs clés")
        st.plotly_chart(fig_amplifiers(v.amplifiers), use_container_width=True)
    with cc2:
        st.subheader("Concentration")
        st.metric("Gini contenu", v.concentration["gini_contenu"])
        st.metric("Gini relais", v.concentration["gini_relais"])
        st.metric("Top 20 sources", f"{v.concentration['top20_share_pct']}% des RT")

with tab2:
    st.caption(f"Méthode {n.method} · {n.k} récits · silhouette {n.silhouette} (exploratoire) · "
               f"{n.n_communities} communautés (modularité {n.modularity})")
    st.subheader("Récits, par risque")
    st.plotly_chart(fig_narratives(n.narratives), use_container_width=True)
    for nar in n.narratives:
        cls = {"élevé": "r-eleve", "moyen": "r-moyen", "faible": "r-faible"}[nar.risk_band]
        with st.expander(f"{nar.name}  —  volume {nar.volume:,}"):
            st.markdown(f"<span class='risk-badge {cls}'>risque {nar.risk_band} · {nar.risk_score}</span>",
                        unsafe_allow_html=True)
            st.write(f"**Termes :** {', '.join(nar.terms)}")
            st.write(f"**% négatif :** {nar.pct_negative}  ·  **textes uniques :** {nar.unique_texts}")
            st.caption(f"Exemple : {nar.example}")
            if nar.risk_rationale:
                st.info(nar.risk_rationale)
    st.subheader("Carte des communautés d'amplification")
    st.caption("Taille = nb de retweeteurs · couleur = négativité · position = jour de pic")
    st.plotly_chart(fig_communities(n.communities), use_container_width=True)

with tab3:
    st.warning("Brouillons IA — **validation humaine obligatoire** avant diffusion.")
    if not report.responses:
        st.write("Aucun brouillon (renseigne un fournisseur LLM + clé pour générer).")
    for r in report.responses:
        with st.expander(f"✍️ {r.narrative_name}", expanded=True):
            st.markdown("**Messages réels ancrant la réponse (RAG) :**")
            for msg, vol, sim in r.evidence:
                st.markdown(f"- _[vol {vol} · sim {sim}]_ {msg[:160]}")
            edited = st.text_area("Réponse (éditable)", value=r.draft, height=160, key=f"d{r.nid}")
            col1, col2 = st.columns([1, 4])
            if col1.button("✅ Valider", key=f"v{r.nid}"):
                st.success("Validée. (À brancher sur votre canal de diffusion.)")
            col2.download_button("⬇️ Exporter", edited, file_name=f"reponse_{r.nid}.txt", key=f"e{r.nid}")
