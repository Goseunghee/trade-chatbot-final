from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime
import pandas as pd
import re


app = FastAPI(
    title="Trade Chatbot API",
    description="무역 데이터 조회 및 챗봇 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 파일 경로
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "trade_data_long.csv"   # 네 CSV 파일명에 맞게 수정 가능
INDEX_FILE = BASE_DIR / "index.html"

REQUIRED_COLUMNS = [
    "country",
    "date",
    "year_month",
    "export_value",
    "import_value",
    "trade_balance"
]

COUNTRY_ALIASES = {
    "미국": "미국",
    "usa": "미국",
    "united states": "미국",
    "us": "미국",
    "한국": "한국",
    "대한민국": "한국",
    "korea": "한국",
    "south korea": "한국",
    "중국": "중국",
    "china": "중국",
    "일본": "일본",
    "japan": "일본"
}


# ---------------------------
# Pydantic Models
# ---------------------------
class AskRequest(BaseModel):
    question: str


class TradeDataCreate(BaseModel):
    country: str
    date: str
    year_month: str
    export_value: int
    import_value: int


class TradeDataUpdate(BaseModel):
    date: Optional[str] = None
    export_value: Optional[int] = None
    import_value: Optional[int] = None


# ---------------------------
# Utility Functions
# ---------------------------
def ensure_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """필수 컬럼을 맞추고 타입을 정리"""
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df.copy()

    df["country"] = df["country"].fillna("").astype(str)
    df["date"] = df["date"].fillna("").astype(str)
    df["year_month"] = df["year_month"].fillna("").astype(str)

    df["export_value"] = pd.to_numeric(df["export_value"], errors="coerce").fillna(0).astype(int)
    df["import_value"] = pd.to_numeric(df["import_value"], errors="coerce").fillna(0).astype(int)

    # year_month가 비어 있으면 date에서 생성
    for idx in df.index:
        if not df.at[idx, "year_month"] and df.at[idx, "date"]:
            df.at[idx, "year_month"] = str(df.at[idx, "date"])[:7]

    df["trade_balance"] = df["export_value"] - df["import_value"]

    return df[REQUIRED_COLUMNS]


def load_data() -> pd.DataFrame:
    """CSV 읽기"""
    if not DATA_FILE.exists():
        empty_df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        return ensure_dataframe(empty_df)

    try:
        df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(DATA_FILE, encoding="cp949")

    return ensure_dataframe(df)


def save_data(df: pd.DataFrame) -> None:
    """CSV 저장"""
    df = ensure_dataframe(df)
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


def normalize_country(country: str) -> str:
    """국가명 정규화"""
    if not country:
        return ""
    key = country.strip().lower()
    return COUNTRY_ALIASES.get(key, country.strip())


def extract_country(question: str, df: pd.DataFrame) -> Optional[str]:
    """질문에서 국가 추출"""
    q = question.lower()

    for alias, country in COUNTRY_ALIASES.items():
        if alias in q:
            return country

    countries = df["country"].dropna().astype(str).unique().tolist()
    for country in countries:
        if country and country.lower() in q:
            return country

    return None


def extract_year_month(question: str) -> Optional[str]:
    """질문에서 YYYY-MM 추출"""
    # 예: 2026-07, 2026/7, 2026년 7월
    match = re.search(r"(20\d{2})\D{0,2}(\d{1,2})", question)
    if not match:
        return None

    year = match.group(1)
    month = int(match.group(2))

    if 1 <= month <= 12:
        return f"{year}-{month:02d}"

    return None


def row_to_dict(row) -> dict:
    """Pandas row를 JSON 직렬화 가능한 dict로 변환"""
    return {
        "country": str(row["country"]),
        "date": str(row["date"]),
        "year_month": str(row["year_month"]),
        "export_value": int(row["export_value"]),
        "import_value": int(row["import_value"]),
        "trade_balance": int(row["trade_balance"]),
    }


def find_latest_row(df: pd.DataFrame, country: Optional[str] = None):
    """최신 데이터 찾기"""
    temp_df = df.copy()

    if country:
        temp_df = temp_df[temp_df["country"] == country]

    if temp_df.empty:
        return None

    temp_df = temp_df.sort_values(by=["year_month", "date"], ascending=False)
    return temp_df.iloc[0]


def find_exact_row(df: pd.DataFrame, country: str, year_month: str):
    """국가 + 년월 일치 데이터 찾기"""
    matched = df[(df["country"] == country) & (df["year_month"] == year_month)]
    if matched.empty:
        return None
    return matched.iloc[0]


def format_trade_answer(row, intent: str) -> str:
    """챗봇 답변 문장 생성"""
    country = row["country"]
    year_month = row["year_month"]
    export_value = int(row["export_value"])
    import_value = int(row["import_value"])
    trade_balance = int(row["trade_balance"])

    if intent == "latest_trade":
        return (
            f"{country}의 최신 데이터는 {year_month} 기준입니다. "
            f"수출은 {export_value:,}, 수입은 {import_value:,}, "
            f"무역수지는 {trade_balance:,}입니다."
        )

    return (
        f"{country}의 {year_month} 무역 데이터입니다. "
        f"수출은 {export_value:,}, 수입은 {import_value:,}, "
        f"무역수지는 {trade_balance:,}입니다."
    )


def save_to_firestore(payload: dict) -> bool:
    """
    Firestore 저장 시도
    - 설정이 없거나 패키지가 없으면 False 반환
    """
    try:
        import firebase_admin
        from firebase_admin import firestore

        if not firebase_admin._apps:
            firebase_admin.initialize_app()

        db = firestore.client()
        db.collection("trade_chat_logs").add(payload)
        return True

    except Exception:
        return False


def handle_trade_question(question: str, df: pd.DataFrame):
    """질문 분석 후 적절한 데이터 반환"""
    if df.empty:
        raise HTTPException(status_code=404, detail="무역 데이터가 없습니다.")

    country = extract_country(question, df)
    year_month = extract_year_month(question)

    # 최신 데이터 요청
    if "최신" in question or "latest" in question.lower():
        row = find_latest_row(df, country)
        if row is None:
            raise HTTPException(status_code=404, detail="해당 국가의 최신 데이터를 찾을 수 없습니다.")
        return row, "latest_trade"

    # 특정 월 요청
    if country and year_month:
        row = find_exact_row(df, country, year_month)
        if row is None:
            raise HTTPException(status_code=404, detail="해당 국가와 월의 데이터를 찾을 수 없습니다.")
        return row, "monthly_trade"

    # 국가만 있고 월이 없으면 최신 데이터 반환