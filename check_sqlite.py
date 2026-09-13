import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "trade_data.db")
print("DB 경로:", db_path)
print("DB 파일 존재:", os.path.exists(db_path))

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

try:
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("\n테이블 목록:")
    for t in tables:
        print(tuple(t))

    print("\ntrade_data 컬럼:")
    columns = cur.execute("PRAGMA table_info(trade_data)").fetchall()
    for col in columns:
        print(tuple(col))

    print("\n샘플 데이터:")
    rows = cur.execute("SELECT * FROM trade_data LIMIT 3").fetchall()
    for row in rows:
        print(dict(row))

except Exception as e:
    print("에러:", e)

finally:
    conn.close()