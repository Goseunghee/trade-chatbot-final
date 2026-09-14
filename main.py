from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional
import csv

app = FastAPI(
    title="Trade Chatbot API",
    description="무역 데이터 기반 챗봇 + CRUD API",
    version="1.0.0"
)

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "data" / "trade_data_long.csv"

INDEX_CANDIDATES = [
    BASE_DIR / "index.html",
    BASE_DIR / "templates" / "index.html",
    BASE_DIR / "static" / "index.html",
]


# ----------------------------
# Pydantic 모델
# ----------------------------
class AskRequest(BaseModel):
    question: str


class TradeCreate(BaseModel):
    country: str
    date: str
    year_month: str
    export_value: int = Field(ge=0)
    import_value: int = Field(ge=0)
    trade_balance: Optional[int] = None


class TradeUpdate(BaseModel):
    date: Optional[str] = None
    export_value: Optional[int] = Field(default=None, ge=0)
    import_value: Optional[int] = Field(default=None, ge=0)
    trade_balance: Optional[int] = None


# ----------------------------
# 공통 유틸
# ----------------------------
def normalize_metric_name(metric: str) -> Optional[str]:
    metric = (metric or "").strip().lower()

    if metric in ["export_value", "수출", "수출금액", "export"]:
        return "export_value"
    if metric in ["import_value", "수입", "수입금액", "import"]:
        return "import_value"
    if metric in ["trade_balance", "무역수지", "balance"]:
        return "trade_balance"

    if "수출" in metric:
        return "export_value"
    if "수입" in metric:
        return "import_value"
    if "무역수지" in metric:
        return "trade_balance"

    return None


def calculate_trade_balance(export_value: int, import_value: int) -> int:
    return export_value - import_value


def format_number(value: int) -> str:
    return f"{value:,}"


def load_trades():
    """
    long 형식 CSV:
    country,metric,unit,date,value,year_month,metric_std

    를 읽어서 wide 형식 리스트로 변환:
    [
      {
        "country": "미국",
        "date": "2026-07-01",
        "year_month": "2026-07",
        "export_value": 17474061,
        "import_value": 8967205,
        "trade_balance": 8506856
      }
    ]
    """
    if not CSV_FILE.exists():
        return []

    grouped = {}

    with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            country = (row.get("country") or "").strip()
            date = (row.get("date") or "").strip()
            year_month = (row.get("year_month") or "").strip()
            metric_raw = row.get("metric_std") or row.get("metric") or ""
            metric_key = normalize_metric_name(metric_raw)
            value_raw = row.get("value", "0")

            if not country or not year_month or not metric_key:
                continue

            try:
                value = int(float(value_raw))
            except ValueError:
                value = 0

            key = (country, year_month)

            if key not in grouped:
                grouped[key] = {
                    "country": country,
                    "date": date,
                    "year_month": year_month,
                    "export_value": 0,
                    "import_value": 0,
                    "trade_balance": 0,
                }

            if date:
                grouped[key]["date"] = date

            grouped[key][metric_key] = value

    rows = list(grouped.values())

    # 무역수지는 일관성 있게 재계산
    for row in rows:
        row["trade_balance"] = calculate_trade_balance(
            row["export_value"],
            row["import_value"]
        )

    rows.sort(key=lambda x: (x["country"], x["year_month"]))
    return rows


def save_trades(rows):
    """
    wide 형식 rows를 다시 long 형식 CSV로 저장
    CSV 원본 형식:
    country,metric,unit,date,value,year_month,metric_std
    """
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)

    long_rows = []
    rows = sorted(rows, key=lambda x: (x["country"], x["year_month"]))

    for row in rows:
        export_value = int(row["export_value"])
        import_value = int(row["import_value"])
        trade_balance = int(row.get("trade_balance", export_value - import_value))

        long_rows.append({
            "country": row["country"],
            "metric": "수출금액",
            "unit": "천불",
            "date": row["date"],
            "value": export_value,
            "year_month": row["year_month"],
            "metric_std": "export_value",
        })
        long_rows.append({
            "country": row["country"],
            "metric": "수입금액",
            "unit": "천불",
            "date": row["date"],
            "value": import_value,
            "year_month": row["year_month"],
            "metric_std": "import_value",
        })
        long_rows.append({
            "country": row["country"],
            "metric": "무역수지",
            "unit": "천불",
            "date": row["date"],
            "value": trade_balance,
            "year_month": row["year_month"],
            "metric_std": "trade_balance",
        })

    with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["country", "metric", "unit", "date", "value", "year_month", "metric_std"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(long_rows)


def classify_intent(question: str) -> str:
    q = (question or "").strip()

    # "최신" 질문은 전체 요약으로 우선 처리
    if "최신" in q or "최근" in q:
        return "latest_trade"
    if "수출" in q:
        return "export_value"
    if "수입" in q:
        return "import_value"
    if "무역수지" in q:
        return "trade_balance"

    return "latest_trade"


def extract_country(question: str, trades: list) -> Optional[str]:
    q = (question or "").strip()
    countries = sorted({row["country"] for row in trades}, key=len, reverse=True)

    for country in countries:
        if country and country in q:
            return country

    # 질문에 국가가 없으면 미국 우선, 없으면 첫 국가
    if "미국" in countries:
        return "미국"
    return countries[0] if countries else None


def get_latest_trade_by_country(country: str, trades: list):
    filtered = [row for row in trades if row["country"] == country]
    if not filtered:
        return None
    return max(filtered, key=lambda x: x["year_month"])


def find_trade(country: str, year_month: str, trades: list):
    for row in trades:
        if row["country"] == country and row["year_month"] == year_month:
            return row
    return None


def build_answer(intent: str, trade: dict) -> str:
    country = trade["country"]
    year_month = trade["year_month"]
    export_value = format_number(trade["export_value"])
    import_value = format_number(trade["import_value"])
    trade_balance = format_number(trade["trade_balance"])

    if intent == "export_value":
        return f"{country}의 최신 수출 데이터는 {year_month} 기준 {export_value}천불입니다."
    if intent == "import_value":
        return f"{country}의 최신 수입 데이터는 {year_month} 기준 {import_value}천불입니다."
    if intent == "trade_balance":
        return f"{country}의 최신 무역수지는 {year_month} 기준 {trade_balance}천불입니다."

    return (
        f"{country}의 최신 데이터는 {year_month} 기준입니다. "
        f"수출은 {export_value}, 수입은 {import_value}, 무역수지는 {trade_balance}입니다."
    )


def try_save_to_firestore(question: str, answer: str, trade: dict) -> bool:
    """
    Firestore 연결 안 했으면 false 반환
    필요하면 나중에 여기만 바꾸면 됨
    """
    return False


# ----------------------------
# 페이지 라우팅
# ----------------------------
@app.get("/", include_in_schema=False)
def home():
    for path in INDEX_CANDIDATES:
        if path.exists():
            return FileResponse(path)
    return {
        "message": "Trade Chatbot API 실행 중입니다.",
        "docs": "/docs"
    }


# ----------------------------
# 챗봇 API
# ----------------------------
@app.post("/ask")
def ask_question(request: AskRequest):
    trades = load_trades()
    if not trades:
        raise HTTPException(status_code=404, detail="무역 데이터가 없습니다.")

    intent = classify_intent(request.question)
    country = extract_country(request.question, trades)

    if not country:
        raise HTTPException(status_code=404, detail="질문에서 국가를 찾을 수 없습니다.")

    latest_trade = get_latest_trade_by_country(country, trades)
    if not latest_trade:
        raise HTTPException(status_code=404, detail=f"{country} 데이터가 없습니다.")

    answer = build_answer(intent, latest_trade)
    firestore_saved = try_save_to_firestore(request.question, answer, latest_trade)

    return {
        "intent": intent,
        "question": request.question,
        "answer": answer,
        "data": latest_trade,
        "firestore_saved": firestore_saved
    }


# ----------------------------
# CRUD API
# ----------------------------
@app.get("/trades")
def get_trades():
    return load_trades()


@app.get("/trades/{country}/{year_month}")
def get_trade(country: str, year_month: str):
    trades = load_trades()
    trade = find_trade(country, year_month, trades)

    if not trade:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")

    return trade


@app.post("/trades")
def create_trade(payload: TradeCreate):
    trades = load_trades()

    existing = find_trade(payload.country, payload.year_month, trades)
    if existing:
        raise HTTPException(status_code=400, detail="이미 같은 국가와 연월 데이터가 존재합니다.")

    trade_balance = (
        payload.trade_balance
        if payload.trade_balance is not None
        else calculate_trade_balance(payload.export_value, payload.import_value)
    )

    new_row = {
        "country": payload.country,
        "date": payload.date,
        "year_month": payload.year_month,
        "export_value": payload.export_value,
        "import_value": payload.import_value,
        "trade_balance": trade_balance,
    }

    trades.append(new_row)
    save_trades(trades)

    return {
        "message": "데이터가 생성되었습니다.",
        "data": new_row
    }


@app.put("/trades/{country}/{year_month}")
def update_trade(country: str, year_month: str, payload: TradeUpdate):
    trades = load_trades()
    trade = find_trade(country, year_month, trades)

    if not trade:
        raise HTTPException(status_code=404, detail="수정할 데이터를 찾을 수 없습니다.")

    if payload.date is not None:
        trade["date"] = payload.date
    if payload.export_value is not None:
        trade["export_value"] = payload.export_value
    if payload.import_value is not None:
        trade["import_value"] = payload.import_value

    if payload.trade_balance is not None:
        trade["trade_balance"] = payload.trade_balance
    else:
        trade["trade_balance"] = calculate_trade_balance(
            trade["export_value"],
            trade["import_value"]
        )

    save_trades(trades)

    return {
        "message": "데이터가 수정되었습니다.",
        "data": trade
    }


@app.delete("/trades/{country}/{year_month}")
def delete_trade(country: str, year_month: str):
    trades = load_trades()
    new_trades = [
        row for row in trades
        if not (row["country"] == country and row["year_month"] == year_month)
    ]

    if len(new_trades) == len(trades):
        raise HTTPException(status_code=404, detail="삭제할 데이터를 찾을 수 없습니다.")

    save_trades(new_trades)

    return {
        "message": "데이터가 삭제되었습니다.",
        "country": country,
        "year_month": year_month
    }


# ----------------------------
# 실행용
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)