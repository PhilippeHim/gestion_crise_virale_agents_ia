from pipeline.ui.react_components import render_crisis_dashboard


def afficher(donnees: dict) -> None:
    """Vue client principale — Crisis Intelligence Center (C-suite dashboard)."""
    render_crisis_dashboard(donnees, height=920)
