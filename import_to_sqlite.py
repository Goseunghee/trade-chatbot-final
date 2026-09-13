import pandas as pd
import sqlite3

# CSV 읽기
df = pd.read_csv("trade_data_clean.csv")

print("원본 컬럼:", df.columns.tolist())

# 컬럼명 통일
rename_map = {}

if "국가별" in df.columns:
    rename_map["국가별"] = "country"
if "연월" in df.columns:
    rename_map["연월"] = "year_month"
if "시점" in df.columns:
    rename_map["시점"] = "year_month"
if "항목" in df.columns:
    rename_map["항목"] = "item"
if "금액" in df.columns:
    rename_map["금액"] = "amount"
if "데이터" in df.columns:
    rename_map["데이터"] = "amount"

df = df.rename(columns=rename_map)

# amount 숫자 변환
if "amount" in df.columns:
    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

# SQLite 저장
conn = sqlite3.connect("trade_data.db")
df.to_sql("trade_data", conn, if_exists="replace", index=False)

# 인덱스 생성
cursor = conn.cursor()
try:
    cursor.execute("CREATE INDEX idx_country ON trade_data(country)")
except:
    pass

try:
    cursor.execute("CREATE INDEX idx_year_month ON trade_data(year_month)")
except:
    pass

try:
    cursor.execute("CREATE INDEX idx_item ON trade_data(item)")
except:
    pass

conn.commit()

# 확인
count = cursor.execute("SELECT COUNT(*) FROM trade_data").fetchone()[0]
print("저장 완료:", count, "행")

conn.close()