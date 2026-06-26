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
