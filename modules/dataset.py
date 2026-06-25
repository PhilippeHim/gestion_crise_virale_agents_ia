from __future__ import annotations

from pathlib import Path
from typing import Any

from datathon_pipeline.config import FilterConfig


def _import_pandas():
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pandas est requis pour cette pipeline. Installe les dependances avec "
            "`venv\\Scripts\\python.exe -m pip install -r requirements.txt`."
        ) from exc
    return pd


def load_dataset(path: str | Path, sheet_name: str | int | None = 0):
    pd = _import_pandas()
    source = Path(path)
    suffix = source.suffix.lower()

    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(source, sheet_name=sheet_name)
    if suffix == ".csv":
        return pd.read_csv(source, sep=None, engine="python")

    raise ValueError(f"Format non supporte: {source.suffix}")


def apply_filters(dataset, filters: list[FilterConfig]):
    filtered = dataset.copy()
    for filter_config in filters:
        if filter_config.column not in filtered.columns:
            raise KeyError(f"Colonne inconnue dans le filtre: {filter_config.column}")
        mask = _build_mask(filtered[filter_config.column], filter_config.op, filter_config.value)
        filtered = filtered[mask]
    return filtered


def _build_mask(series, op: str, value: Any):
    pd = _import_pandas()
    normalized_op = op.lower()

    if normalized_op in {"eq", "equals", "=="}:
        return series == value
    if normalized_op in {"ne", "not_equals", "!="}:
        return series != value
    if normalized_op == "in":
        return series.isin(_as_list(value))
    if normalized_op == "not_in":
        return ~series.isin(_as_list(value))
    if normalized_op == "contains":
        return series.astype(str).str.contains(str(value), case=False, na=False)
    if normalized_op == "not_contains":
        return ~series.astype(str).str.contains(str(value), case=False, na=False)
    if normalized_op in {"gt", "gte", "lt", "lte"}:
        comparable_series, comparable_value = _coerce_comparable(pd, series, value)
        if normalized_op == "gt":
            return comparable_series > comparable_value
        if normalized_op == "gte":
            return comparable_series >= comparable_value
        if normalized_op == "lt":
            return comparable_series < comparable_value
        return comparable_series <= comparable_value
    if normalized_op == "between":
        start, end = value
        comparable_series, start_value = _coerce_comparable(pd, series, start)
        _, end_value = _coerce_comparable(pd, series, end)
        return comparable_series.between(start_value, end_value, inclusive="both")
    if normalized_op == "is_null":
        return series.isna()
    if normalized_op == "not_null":
        return series.notna()

    raise ValueError(f"Operateur de filtre non supporte: {op}")


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return [value]


def _coerce_comparable(pd, series, value: Any):
    numeric_series = pd.to_numeric(series, errors="coerce")
    numeric_value = pd.to_numeric(value, errors="coerce")
    if not pd.isna(numeric_value) and numeric_series.notna().any():
        return numeric_series, numeric_value

    date_series = pd.to_datetime(series, errors="coerce")
    date_value = pd.to_datetime(value, errors="coerce")
    if not pd.isna(date_value) and date_series.notna().any():
        return date_series, date_value

    return series.astype(str), str(value)
