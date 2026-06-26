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

        function ListBlock({{ title, items }}) {{
          return e("section", {{ style: {{ ...styles.band, marginTop: 12 }} }},
            e("h2", {{ style: {{ ...styles.title, fontSize: 22, textAlign: "left", marginBottom: 12 }} }}, title),
            items && items.length
              ? e("div", {{ style: {{ display: "grid", gap: 8 }} }},
                  items.map((item, index) => e("div", {{
                    key: index,
                    style: {{
                      borderLeft: `4px solid ${{palette.accent}}`,
                      background: palette.soft,
                      borderRadius: 8,
                      padding: "10px 12px",
                      lineHeight: 1.4
                    }}
                  }}, item))
                )
              : e("div", {{ style: styles.caption }}, "Non disponible")
          );
        }}

        function CrisisDashboard({{ payload }}) {{
          const proposition = payload.proposition || {{}};
          const chiffres = proposition.chiffres_cles || {{}};
          const pic = chiffres.pic || {{}};
          const recit = proposition.recit_prioritaire || {{}};
          const recits = payload.recits || [];
          const messages = proposition.messages_cles || [];
          const diagnostic = proposition.diagnostic || [];
          const validation = proposition.points_a_valider || [];
          const eviter = proposition.messages_a_eviter || [];
          const communities = payload.communautes || [];

          const metrics = [
            {{ label: "Messages analyses", value: chiffres.messages_analyses ?? 0, caption: payload.periode_collecte || "periode n/a" }},
            {{ label: "Pic maximal", value: pic.messages ?? 0, caption: pic.date || "date n/a", tone: "warn" }},
            {{ label: "Recits structurants", value: chiffres.nombre_recits ?? recits.length, caption: recits.slice(0, 3).map((r) => r.nom).filter(Boolean).join(" | ") }},
            {{ label: "Priorite", value: proposition.priorite || "n/a", caption: proposition.niveau_risque || "", tone: proposition.priorite === "Haute" ? "danger" : "warn" }}
          ];

          return e("main", {{ style: {{ ...styles.wrap, display: "grid", gap: 12 }} }},
            e(Header, {{
              title: "Synthese executive - Crise informationnelle",
              subtitle: payload.periode_collecte || proposition.public_cible || "Vue decisionnelle"
            }}),
            e(Summary, {{ metrics }}),
            e("section", {{ style: {{ ...styles.band }} }},
              e("h2", {{ style: {{ ...styles.title, fontSize: 24, marginBottom: 10 }} }}, proposition.titre || "Diagnostic de crise"),
              e("p", {{ style: {{ fontSize: 16, lineHeight: 1.5, margin: 0, color: palette.ink }} }},
                proposition.synthese_executive || "Synthese non disponible."
              )
            ),
            e("section", {{ style: {{ display: "grid", gridTemplateColumns: "1.15fr .85fr", gap: 12 }} }},
              e("article", {{ style: styles.band }},
                e("h2", {{ style: {{ ...styles.title, fontSize: 22, textAlign: "left", marginBottom: 10 }} }}, "Priorite de communication"),
                e("div", {{ style: {{ display: "grid", gap: 8 }} }},
                  e(MetricCard, {{ label: "Strategie recommandee", value: proposition.strategie || "n/a", caption: proposition.delai_recommande || "" }}),
                  e(MetricCard, {{ label: "Recit prioritaire", value: recit.nom || "n/a", caption: `${{recit.volume ?? "n/a"}} messages · ${{recit.pct_negative ?? "n/a"}}% negatif · risque ${{recit.score_risque ?? "n/a"}}`, tone: "danger" }})
                )
              ),
              e("article", {{ style: styles.band }},
                e("h2", {{ style: {{ ...styles.title, fontSize: 22, textAlign: "left", marginBottom: 10 }} }}, "Signaux de coordination"),
                e("div", {{ style: {{ display: "grid", gap: 8 }} }},
                  e(MetricCard, {{ label: "Communautes", value: communities.length }}),
                  e(MetricCard, {{ label: "Part negative", value: `${{chiffres.part_negative ?? "n/a"}}%`, tone: "warn" }})
                )
              )
            ),
            e(ListBlock, {{ title: "Diagnostic", items: diagnostic }}),
            e(ListBlock, {{ title: "Messages cles", items: messages }}),
            e("section", {{ style: {{ ...styles.band }} }},
              e("h2", {{ style: {{ ...styles.title, fontSize: 22, textAlign: "left", marginBottom: 10 }} }}, "Brouillon de reponse"),
              e("div", {{
                style: {{
                  background: palette.soft,
                  border: `1px solid ${{palette.line}}`,
                  borderRadius: 8,
                  padding: 14,
                  lineHeight: 1.5,
                  whiteSpace: "pre-wrap"
                }}
              }}, proposition.reponse_brouillon || "Brouillon non disponible.")
            ),
            e("section", {{ style: {{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }} }},
              e(ListBlock, {{ title: "A eviter", items: eviter }}),
              e(ListBlock, {{ title: "A valider", items: validation }})
            )
          );
        }}

        function CrisisDashboardTop({{ payload }}) {{
          const proposition = payload.proposition || {{}};
          const chiffres = proposition.chiffres_cles || {{}};
          const pic = chiffres.pic || {{}};
          const recit = proposition.recit_prioritaire || {{}};
          const recits = payload.recits || [];
          const communities = payload.communautes || [];

          const metrics = [
            {{ label: "Messages analyses", value: chiffres.messages_analyses ?? 0, caption: payload.periode_collecte || "periode n/a" }},
            {{ label: "Pic maximal", value: pic.messages ?? 0, caption: pic.date || "date n/a", tone: "warn" }},
            {{ label: "Recits structurants", value: chiffres.nombre_recits ?? recits.length, caption: recits.slice(0, 3).map((r) => r.nom).filter(Boolean).join(" | ") }},
            {{ label: "Priorite", value: proposition.priorite || "n/a", caption: proposition.niveau_risque || "", tone: proposition.priorite === "Haute" ? "danger" : "warn" }}
          ];

          return e("main", {{ style: {{ ...styles.wrap, display: "grid", gap: 12 }} }},
            e(Header, {{
              title: "Synthese executive - Crise informationnelle",
              subtitle: payload.periode_collecte || proposition.public_cible || "Vue decisionnelle"
            }}),
            e(Summary, {{ metrics }}),
            e("section", {{ style: {{ ...styles.band }} }},
              e("h2", {{ style: {{ ...styles.title, fontSize: 24, marginBottom: 10 }} }}, proposition.titre || "Diagnostic de crise"),
              e("p", {{ style: {{ fontSize: 16, lineHeight: 1.5, margin: 0, color: palette.ink }} }},
                proposition.synthese_executive || "Synthese non disponible."
              )
            ),
            e("section", {{ style: {{ display: "grid", gridTemplateColumns: "1.15fr .85fr", gap: 12 }} }},
              e("article", {{ style: styles.band }},
                e("h2", {{ style: {{ ...styles.title, fontSize: 22, textAlign: "left", marginBottom: 10 }} }}, "Priorite de communication"),
                e("div", {{ style: {{ display: "grid", gap: 8 }} }},
                  e(MetricCard, {{ label: "Strategie recommandee", value: proposition.strategie || "n/a", caption: proposition.delai_recommande || "" }}),
                  e(MetricCard, {{ label: "Recit prioritaire", value: recit.nom || "n/a", caption: `${{recit.volume ?? "n/a"}} messages · ${{recit.pct_negative ?? "n/a"}}% negatif · risque ${{recit.score_risque ?? "n/a"}}`, tone: "danger" }})
                )
              ),
              e("article", {{ style: styles.band }},
                e("h2", {{ style: {{ ...styles.title, fontSize: 22, textAlign: "left", marginBottom: 10 }} }}, "Signaux de coordination"),
                e("div", {{ style: {{ display: "grid", gap: 8 }} }},
                  e(MetricCard, {{ label: "Communautes", value: communities.length }}),
                  e(MetricCard, {{ label: "Part negative", value: `${{chiffres.part_negative ?? "n/a"}}%`, tone: "warn" }})
                )
              )
            )
          );
        }}

        function CrisisDashboardBottom({{ payload }}) {{
          const proposition = payload.proposition || {{}};
          const messages = proposition.messages_cles || [];
          const diagnostic = proposition.diagnostic || [];
          const validation = proposition.points_a_valider || [];
          const eviter = proposition.messages_a_eviter || [];

          return e("main", {{ style: {{ ...styles.wrap, display: "grid", gap: 12 }} }},
            e(ListBlock, {{ title: "Diagnostic", items: diagnostic }}),
            e(ListBlock, {{ title: "Messages cles", items: messages }}),
            e("section", {{ style: {{ ...styles.band }} }},
              e("h2", {{ style: {{ ...styles.title, fontSize: 22, textAlign: "left", marginBottom: 10 }} }}, "Brouillon de reponse"),
              e("div", {{
                style: {{
                  background: palette.soft,
                  border: `1px solid ${{palette.line}}`,
                  borderRadius: 8,
                  padding: 14,
                  lineHeight: 1.5,
                  whiteSpace: "pre-wrap"
                }}
              }}, proposition.reponse_brouillon || "Brouillon non disponible.")
            ),
            e("section", {{ style: {{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }} }},
              e(ListBlock, {{ title: "A eviter", items: eviter }}),
              e(ListBlock, {{ title: "A valider", items: validation }})
            )
          );
        }}

        const registry = {{ Header, Summary, Steps, Outputs, CrisisDashboard, CrisisDashboardTop, CrisisDashboardBottom }};
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


def render_crisis_dashboard(donnees: dict, height: int = 920) -> None:
    proposition = donnees.get("proposition") or {}
    narratif = donnees.get("narratif") or {}
    payload = {
        "proposition": proposition,
        "recits": narratif.get("recits", []) if isinstance(narratif, dict) else [],
        "communautes": donnees.get("communautes", []),
        "periode_collecte": donnees.get("periode_collecte"),
    }
    _render_react("CrisisDashboard", {"payload": payload}, height=height)
