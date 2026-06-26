import html as _html
import json
from typing import Any

import pandas as pd
import streamlit.components.v1 as components


def _json_default(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _render_react(component_name: str, props: dict, height: int) -> None:
    props_json = json.dumps(props, ensure_ascii=False, default=_json_default)
    component_json = json.dumps(component_name)

    components.html(
        f"""
        <div id="react-root"></div>
        <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
        <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
        <script>
        const e = React.createElement;
        const props = {props_json};
        const componentName = {component_json};

        const palette = {{
          ink: "#172026",
          muted: "#64717d",
          line: "#d8dee4",
          panel: "#ffffff",
          soft: "#f6f8fa",
          accent: "#0f6b5f",
          warn: "#b7791f",
          danger: "#b42318",
          ok: "#15803d"
        }};

        const styles = {{
          wrap: {{
            fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            color: palette.ink,
            boxSizing: "border-box"
          }},
          band: {{
            border: `1px solid ${{palette.line}}`,
            borderRadius: 8,
            background: palette.panel,
            padding: 16,
            boxSizing: "border-box"
          }},
          row: {{
            display: "grid",
            gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
            gap: 12
          }},
          metric: {{
            border: `1px solid ${{palette.line}}`,
            borderRadius: 8,
            background: palette.soft,
            padding: "12px 14px",
            minHeight: 82,
            boxSizing: "border-box"
          }},
          label: {{
            fontSize: 12,
            color: palette.muted,
            marginBottom: 8,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis"
          }},
          value: {{
            fontSize: 26,
            lineHeight: 1.1,
            fontWeight: 750
          }},
          caption: {{
            fontSize: 12,
            color: palette.muted,
            marginTop: 8
          }},
          title: {{
            fontFamily: "HK Grotesk, HKGrotesk, Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            fontSize: 28,
            fontWeight: 800,
            margin: "0 0 6px",
            textAlign: "center",
            letterSpacing: 0
          }},
          subtitle: {{
            fontSize: 14,
            color: palette.muted,
            margin: 0,
            textAlign: "center"
          }}
        }};

        function Header({{ title, subtitle }}) {{
          return e("section", {{ style: {{ ...styles.wrap, ...styles.band, marginBottom: 10 }} }},
            e("h1", {{ style: styles.title }}, title),
            e("p", {{ style: styles.subtitle }}, subtitle)
          );
        }}

        function MetricCard({{ label, value, caption, tone }}) {{
          const toneColor = tone === "danger" ? palette.danger : tone === "warn" ? palette.warn : tone === "ok" ? palette.ok : palette.ink;
          return e("article", {{ style: styles.metric }},
            e("div", {{ style: styles.label }}, label),
            e("div", {{ style: {{ ...styles.value, color: toneColor }} }}, value),
            caption ? e("div", {{ style: styles.caption }}, caption) : null
          );
        }}

        function Summary({{ metrics }}) {{
          return e("section", {{ style: {{ ...styles.wrap, ...styles.row }} }},
            metrics.map((metric, index) => e(MetricCard, {{ key: index, ...metric }}))
          );
        }}

        function StatusPill({{ status }}) {{
          const color = status === "fait" ? palette.ok : status === "erreur" ? palette.danger : palette.warn;
          return e("span", {{
            style: {{
              display: "inline-flex",
              alignItems: "center",
              border: `1px solid ${{color}}`,
              color,
              borderRadius: 999,
              padding: "3px 8px",
              fontSize: 12,
              fontWeight: 700
            }}
          }}, status);
        }}

        function Steps({{ steps }}) {{
          return e("section", {{ style: {{ ...styles.wrap, ...styles.band }} }},
            e("div", {{ style: {{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10 }} }},
              steps.map((step, index) => e("article", {{
                key: index,
                style: {{
                  border: `1px solid ${{palette.line}}`,
                  borderRadius: 8,
                  padding: 12,
                  background: step.statut === "erreur" ? "#fff5f5" : "#fbfcfd",
                  minHeight: 92
                }}
              }},
                e("div", {{ style: {{ fontWeight: 750, marginBottom: 10 }} }}, step.module),
                e(StatusPill, {{ status: step.statut }}),
                e("div", {{ style: styles.caption }},
                  `${{step.lignes_avant ?? "n/a"}} -> ${{step.lignes_apres ?? "n/a"}} lignes`
                )
              ))
            )
          );
        }}

        function JsonBlock({{ value }}) {{
          return e("pre", {{
            style: {{
              background: "#0b1220",
              color: "#d6e4ff",
              borderRadius: 8,
              padding: 14,
              overflow: "auto",
              fontSize: 12,
              lineHeight: 1.45,
              maxHeight: 420
            }}
          }}, JSON.stringify(value, null, 2));
        }}

        function Outputs({{ payload }}) {{
          const communities = payload.communautes || [];
          return e("section", {{ style: {{ ...styles.wrap, ...styles.band }} }},
            e("div", {{ style: {{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12, marginBottom: 14 }} }},
              e(MetricCard, {{ label: "Pipeline arrete", value: payload.arreter_pipeline ? "Oui" : "Non", tone: payload.arreter_pipeline ? "warn" : "ok" }}),
              e(MetricCard, {{ label: "Communautes retenues", value: communities.length }}),
              e(MetricCard, {{ label: "Proposition", value: payload.proposition ? "Disponible" : "A produire", tone: payload.proposition ? "ok" : "warn" }})
            ),
            communities.length
              ? e("div", {{ style: {{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10, marginBottom: 14 }} }},
                  communities.map((community) => e("article", {{ key: community.id, style: styles.metric }},
                    e("div", {{ style: {{ fontWeight: 800 }} }}, `Communaute ${{community.id}}`),
                    e("div", {{ style: styles.caption }}, `${{community.nombre_messages}} messages · ${{community.pct_negative}}% negatif`),
                    e("div", {{ style: styles.caption }}, `Pic: ${{community.jour_pic || "n/a"}}`),
                    e("div", {{ style: styles.caption }}, `Sources: ${{(community.sources_pivots || []).map((item) => item[0]).join(", ") || "n/a"}}`)
                  ))
                )
              : null,
            e(JsonBlock, {{ value: payload }})
          );
        }}

        const registry = {{ Header, Summary, Steps, Outputs }};
        ReactDOM.createRoot(document.getElementById("react-root")).render(
          e(registry[componentName], props)
        );
        </script>
        """,
        height=height,
        scrolling=True,
    )


def render_react_header(title: str, subtitle: str) -> None:
    _render_react("Header", {"title": title, "subtitle": subtitle}, height=112)


def render_react_summary(metrics: list[dict]) -> None:
    _render_react("Summary", {"metrics": metrics}, height=110)


def render_react_steps(steps: list[dict]) -> None:
    height = 150 + max(0, (len(steps) - 4) // 4) * 110
    _render_react("Steps", {"steps": steps}, height=height)


def render_react_outputs(payload: dict) -> None:
    height = 520 if payload.get("communautes") else 360
    _render_react("Outputs", {"payload": payload}, height=height)


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD C-SUITE — page unique, sans onglets (Crisis Intelligence Center)
# ─────────────────────────────────────────────────────────────────────────────

def _build_cic_html(donnees: dict) -> str:
    """Génère le HTML complet du Crisis Intelligence Center (page unique, sans onglets)."""

    proposition = donnees.get("proposition") or {}
    narratif    = donnees.get("narratif") or {}
    dataset     = donnees.get("dataset")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    chiffres = proposition.get("chiffres_cles") or {}

    messages_analyses = chiffres.get("messages_analyses", 0)
    if isinstance(dataset, pd.DataFrame) and not dataset.empty:
        messages_analyses = messages_analyses or len(dataset)

    pic          = chiffres.get("pic") or {}
    pic_messages = pic.get("messages", 0)
    pic_date     = pic.get("date", "n/a")

    recits        = narratif.get("recits", []) if isinstance(narratif, dict) else []
    nombre_recits = len(recits)

    priorite_val  = proposition.get("priorite", "n/a")
    delai         = proposition.get("delai_recommande", "n/a")
    niveau_risque = proposition.get("niveau_risque", "n/a")

    messages_a_eviter = proposition.get("messages_a_eviter") or []
    points_a_valider  = proposition.get("points_a_valider") or []
    reponse_brouillon = proposition.get("reponse_brouillon") or ""

    # ── Badge risque ──────────────────────────────────────────────────────────
    risque_lower = str(niveau_risque).lower()
    if risque_lower in ("élevé", "eleve", "high", "critique"):
        risque_classe = "badge-danger"
    elif risque_lower in ("moyen", "medium", "modéré", "modere"):
        risque_classe = "badge-warning"
    else:
        risque_classe = "badge-ok"
    risque_label = f"Risque {niveau_risque}" if niveau_risque != "n/a" else "Risque inconnu"

    # ── Séries temporelles depuis dataset ─────────────────────────────────────
    volume_labels_js = "[]"
    volume_data_js   = "[]"
    neg_data_js      = "[]"
    neu_data_js      = "[]"
    pos_data_js      = "[]"
    senti_labels_js  = "[]"

    if isinstance(dataset, pd.DataFrame) and not dataset.empty and "Date" in dataset.columns:
        base = dataset.copy()
        base["Date"] = pd.to_datetime(base["Date"], errors="coerce")
        base = base.dropna(subset=["Date"])

        if not base.empty:
            quotidien = base.set_index("Date").resample("D").size().reset_index(name="n")
            vol_labels = [d.strftime("%d/%m") for d in quotidien["Date"]]
            vol_vals   = quotidien["n"].tolist()
            volume_labels_js = json.dumps(vol_labels)
            volume_data_js   = json.dumps(vol_vals)
            senti_labels_js  = volume_labels_js

            if "Sentiment" in base.columns:
                senti = base.copy()
                senti["jour"] = senti["Date"].dt.date
                pivot = (
                    senti.groupby(["jour", "Sentiment"])
                    .size()
                    .unstack(fill_value=0)
                )
                days = [d.strftime("%d/%m") for d in pd.to_datetime(list(pivot.index))]
                senti_labels_js = json.dumps(days)
                neg_data_js = json.dumps(
                    pivot.get("negative", pd.Series([0] * len(days))).tolist()
                )
                neu_data_js = json.dumps(
                    pivot.get("neutral",  pd.Series([0] * len(days))).tolist()
                )
                pos_data_js = json.dumps(
                    pivot.get("positive", pd.Series([0] * len(days))).tolist()
                )

    # ── Listes HTML : à éviter / à valider ───────────────────────────────────
    def _li_items(items: list, klass: str, prefix: str) -> str:
        if not items:
            return '<div class="cc-empty">Aucun élément disponible.</div>'
        return "".join(
            f'<div class="{klass}"><span class="cc-item-prefix">{prefix}</span>'
            f'{_html.escape(str(item))}</div>'
            for item in items
        )

    msgs_eviter_html  = _li_items(messages_a_eviter, "cc-avoid-item",    "✕")
    msgs_valider_html = _li_items(points_a_valider,  "cc-validate-item", "✓")

    brouillon_html = _html.escape(reponse_brouillon)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.44.0/tabler-icons.min.css">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --bg:        #f8fafc;
  --surface:   #ffffff;
  --border:    #e2e8f0;
  --border-s:  #cbd5e1;
  --text:      #0f172a;
  --text-2:    #475569;
  --text-3:    #94a3b8;
  --danger:    #dc2626;
  --danger-bg: #fef2f2;
  --danger-b:  #fecaca;
  --danger-t:  #991b1b;
  --warn:      #d97706;
  --warn-bg:   #fffbeb;
  --warn-b:    #fde68a;
  --warn-t:    #92400e;
  --ok:        #16a34a;
  --ok-bg:     #f0fdf4;
  --ok-b:      #bbf7d0;
  --ok-t:      #14532d;
  --r: 8px;
}}
body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.5; }}

/* TOPBAR */
.topbar {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 20px; background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 100;
}}
.brand {{ font-family: 'Space Grotesk', sans-serif; font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
.pulse {{ width: 8px; height: 8px; border-radius: 50%; background: var(--danger); animation: blink 1.6s ease-in-out infinite; }}
@keyframes blink {{ 0%,100%{{opacity:1;transform:scale(1)}} 50%{{opacity:.45;transform:scale(1.5)}} }}
.topbar-right {{ display: flex; align-items: center; gap: 10px; }}
.badge-danger  {{ font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;letter-spacing:.5px;text-transform:uppercase;background:var(--danger-bg);color:var(--danger-t);border:1px solid var(--danger-b);animation:badgepulse 2s ease-in-out infinite; }}
.badge-warning {{ font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;letter-spacing:.5px;text-transform:uppercase;background:var(--warn-bg);color:var(--warn-t);border:1px solid var(--warn-b); }}
.badge-ok      {{ font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;letter-spacing:.5px;text-transform:uppercase;background:var(--ok-bg);color:var(--ok-t);border:1px solid var(--ok-b); }}
@keyframes badgepulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.55}} }}
.ts {{ font-size:11px; color:var(--text-3); }}

/* LAYOUT */
.body {{ padding: 16px 20px; display: flex; flex-direction: column; gap: 18px; }}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}

/* KPI ROW */
.kpi-row {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; }}
.kpi {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }}
.kpi.danger  {{ border-color: var(--danger-b); background: var(--danger-bg); }}
.kpi.warning {{ border-color: var(--warn-b);   background: var(--warn-bg); }}
.kpi-label {{ font-size:10px; color:var(--text-3); text-transform:uppercase; letter-spacing:.6px; font-weight:600; margin-bottom:5px; }}
.kpi-value {{ font-family:'Space Grotesk',sans-serif; font-size:26px; font-weight:700; line-height:1; }}
.kpi.danger  .kpi-value {{ color: var(--danger); }}
.kpi.warning .kpi-value {{ color: var(--warn); }}
.kpi-sub {{ font-size:10px; color:var(--text-3); margin-top:4px; }}

/* CARD */
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }}

/* SECTION HEADER */
.sec-hdr {{
  font-size:10px; font-weight:700; text-transform:uppercase;
  letter-spacing:.7px; color:var(--text-3);
  padding-bottom:8px; border-bottom:1px solid var(--border); margin-bottom:10px;
}}

/* ITEM LISTS */
.cc-avoid-item, .cc-validate-item {{
  font-size:12px; color:var(--text); padding:8px 10px;
  background:var(--bg); border-radius:6px;
  display:flex; align-items:flex-start; gap:8px; line-height:1.55;
  margin-bottom: 6px;
}}
.cc-avoid-item    {{ border-left:3px solid var(--danger); }}
.cc-validate-item {{ border-left:3px solid var(--ok); }}
.cc-item-prefix   {{ font-weight:800; flex-shrink:0; font-size:13px; }}
.cc-avoid-item    .cc-item-prefix {{ color:var(--danger); }}
.cc-validate-item .cc-item-prefix {{ color:var(--ok); }}
.cc-empty {{ font-size:12px; color:var(--text-3); font-style:italic; padding:8px 0; }}

/* DRAFT */
.draft-area {{
  width:100%; min-height:110px; padding:10px 12px;
  background:var(--bg); border:1px solid var(--border);
  border-radius:var(--r); font-size:13px; color:var(--text);
  font-family:'Inter',sans-serif; resize:vertical; line-height:1.55;
}}
.draft-area:focus {{ outline:none; border-color:#2563eb; box-shadow:0 0 0 3px #eff6ff; }}
.action-row {{ display:flex; gap:8px; margin-top:8px; }}
.btn {{
  font-family:'Inter',sans-serif; font-size:12px; font-weight:500;
  padding:7px 14px; border-radius:var(--r); border:1px solid var(--border-s);
  background:var(--surface); color:var(--text); cursor:pointer;
  display:flex; align-items:center; gap:5px; transition:background .12s;
}}
.btn:hover {{ background:var(--bg); }}
</style>
</head>
<body>

<!-- ① TOPBAR -->
<div class="topbar">
  <div class="brand">
    <span class="pulse"></span>
    Crisis Intelligence Center
  </div>
  <div class="topbar-right">
    <span class="{risque_classe}">{risque_label}</span>
    <span class="ts" id="cc-ts"></span>
  </div>
</div>

<div class="body">

  <!-- ② KPIs -->
  <div class="kpi-row">
    <div class="kpi danger">
      <div class="kpi-label">Messages analysés</div>
      <div class="kpi-value">{messages_analyses:,}</div>
      <div class="kpi-sub">Total de la collecte</div>
    </div>
    <div class="kpi danger">
      <div class="kpi-label">Pic maximal</div>
      <div class="kpi-value">{pic_messages:,}</div>
      <div class="kpi-sub">{_html.escape(str(pic_date))}</div>
    </div>
    <div class="kpi warning">
      <div class="kpi-label">Récits structurants</div>
      <div class="kpi-value">{nombre_recits}</div>
      <div class="kpi-sub">Narratifs identifiés</div>
    </div>
    <div class="kpi danger">
      <div class="kpi-label">Niveau de priorité</div>
      <div class="kpi-value">{_html.escape(str(priorite_val)).upper()}</div>
      <div class="kpi-sub">Délai : {_html.escape(str(delai))}</div>
    </div>
  </div>

  <!-- ③ DEUX GRAPHIQUES CÔTE À CÔTE -->
  <div class="two-col">
    <div class="card">
      <div class="sec-hdr">Volume quotidien de messages</div>
      <div style="position:relative;width:100%;height:200px;">
        <canvas id="volumeChart"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="sec-hdr">Tonalité au fil du temps</div>
      <div style="position:relative;width:100%;height:200px;">
        <canvas id="tonaliteChart"></canvas>
      </div>
    </div>
  </div>

  <!-- ④ DEUX BLOCS DE DÉCISION CÔTE À CÔTE -->
  <div class="two-col">
    <div class="card">
      <div class="sec-hdr">À éviter</div>
      {msgs_eviter_html}
    </div>
    <div class="card">
      <div class="sec-hdr">À valider</div>
      {msgs_valider_html}
    </div>
  </div>

  <!-- ⑤ BROUILLON DE RÉPONSE -->
  <div class="card">
    <div class="sec-hdr">Brouillon de réponse</div>
    <textarea class="draft-area" id="draft-text">{brouillon_html}</textarea>
    <div class="action-row">
      <button class="btn" onclick="copyDraft(this)">
        <i class="ti ti-copy"></i> Copier
      </button>
    </div>
  </div>

</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
// Horodatage
(function tick() {{
  const el = document.getElementById('cc-ts');
  if (el) el.textContent = 'Mis à jour : ' + new Date().toLocaleTimeString('fr-FR', {{hour:'2-digit',minute:'2-digit',second:'2-digit'}});
  setTimeout(tick, 10000);
}})();

// Données réelles (vides = fallback démo)
const volumeLabels = {volume_labels_js};
const volumeData   = {volume_data_js};
const sentiLabels  = {senti_labels_js};
const negData      = {neg_data_js};
const neuData      = {neu_data_js};
const posData      = {pos_data_js};

const gridC  = 'rgba(0,0,0,0.06)';
const mutedC = '#94a3b8';

// Fallback démo
const dL = ['J-7','J-6','J-5','J-4','J-3','J-2','J-1','Auj.'];
const dV = [320,480,612,890,2100,3841,2940,1820];
const dN = [180,270,380,610,1560,2810,2100,1240];
const dU = [110,160,180,220,420,780,620,420];
const dP = [30,50,52,60,120,251,220,160];

// Graphique Volume
new Chart(document.getElementById('volumeChart'), {{
  type: 'line',
  data: {{
    labels: volumeLabels.length ? volumeLabels : dL,
    datasets: [{{
      label: 'Messages',
      data:  volumeData.length  ? volumeData  : dV,
      borderColor: '#2563eb',
      backgroundColor: 'rgba(37,99,235,0.10)',
      borderWidth: 2, fill: true, tension: .35, pointRadius: 3
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ color: gridC }}, ticks: {{ color: mutedC, font: {{ size: 11 }} }} }},
      y: {{ grid: {{ color: gridC }}, ticks: {{ color: mutedC, font: {{ size: 11 }} }} }}
    }}
  }}
}});

// Graphique Tonalité (aires empilées)
const hasSenti = negData.length > 0;
const sL = hasSenti ? sentiLabels : (volumeLabels.length ? volumeLabels : dL);
new Chart(document.getElementById('tonaliteChart'), {{
  type: 'line',
  data: {{
    labels: sL,
    datasets: [
      {{ label:'Négatif', data: hasSenti ? negData : dN, borderColor:'#dc2626', backgroundColor:'rgba(220,38,38,0.15)', fill:true, borderWidth:2, tension:.35, pointRadius:3, order:1 }},
      {{ label:'Neutre',  data: hasSenti ? neuData : dU, borderColor:'#3266ad', backgroundColor:'rgba(50,102,173,0.10)', fill:true, borderWidth:2, tension:.35, pointRadius:3, order:2 }},
      {{ label:'Positif', data: hasSenti ? posData : dP, borderColor:'#16a34a', backgroundColor:'rgba(22,163,74,0.08)',  fill:true, borderWidth:2, tension:.35, pointRadius:3, order:3 }}
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display:true, position:'top', labels: {{ boxWidth:10, font: {{ size:11 }} }} }} }},
    scales: {{
      x: {{ stacked:true, grid:{{ color:gridC }}, ticks:{{ color:mutedC, font:{{ size:10 }} }} }},
      y: {{ stacked:true, grid:{{ color:gridC }}, ticks:{{ color:mutedC, font:{{ size:10 }} }} }}
    }}
  }}
}});

// Copier brouillon
function copyDraft(btn) {{
  const txt = document.getElementById('draft-text').value;
  navigator.clipboard.writeText(txt).catch(() => {{}});
  const orig = btn.innerHTML;
  btn.innerHTML = '<i class="ti ti-check"></i> Copié !';
  setTimeout(() => {{ btn.innerHTML = orig; }}, 2000);
}}
</script>
</body>
</html>
"""


def render_crisis_dashboard(donnees: dict, height: int = 700) -> None:
    """Affiche le Crisis Intelligence Center (page unique C-suite) dans Streamlit."""
    components.html(_build_cic_html(donnees), height=height, scrolling=True)
