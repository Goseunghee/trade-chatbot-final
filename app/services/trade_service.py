from functools import lru_cache
from pathlib import Path
import difflib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "processed" / "trade_data_clean.csv"


@lru_cache
def load_trade_data():
    df = pd.read_csv(DATA_PATH)
    df["country"] = df["country"].astype(str).str.strip()
    df["year_month"] = df["year_month"].astype(str).str.strip()
    return df


def get_all_countries():
    df = load_trade_data()
    return sorted(df["country"].unique().tolist())


def resolve_country_name(query: str):
    countries = get_all_countries()
    query = query.strip()

    if query in countries:
        return query, []

    partial = [c for c in countries if query in c]
    if partial:
        return partial[0], partial[:5]

    suggestions = difflib.get_close_matches(query, countries, n=5, cutoff=0.3)
    return None, suggestions


def get_latest_trade_data(country: str):
    df = load_trade_data()
    result = df[df["country"] == country].sort_values("date")
    if result.empty:
        return None
    return result.iloc[-1].to_dict()


def get_country_monthly_data(country: str):
    df = load_trade_data()
    result = df[df["country"] == country].sort_values("date")
    return result.to_dict(orient="records")


def get_trade_balance_ranking(year_month=None, limit=5, order="desc"):
    df = load_trade_data()

    if year_month is None:
        year_month = df["year_month"].max()

    month_df = df[df["year_month"] == year_month].copy()
    if month_df.empty:
        return None

    ascending = (order == "asc")
    month_df = month_df.sort_values("trade_balance", ascending=ascending).head(limit)

    return {
        "year_month": year_month,
        "order": order,
        "results": month_df[["country", "export_value", "import_value", "trade_balance"]].to_dict(orient="records")
    }