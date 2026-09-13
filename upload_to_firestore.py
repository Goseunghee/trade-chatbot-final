from pathlib import Path
import math
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
SERVICE_ACCOUNT_PATH = BASE_DIR / "serviceAccountKey.json"
CSV_PATH = BASE_DIR / "trade_data_clean.csv"

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(str(SERVICE_ACCOUNT_PATH))
    firebase_admin.initialize_app(cred)

db = firestore.client()
COLLECTION_NAME = "trade_data"


def clean_value(value):
    """NaN 값을 None으로 바꿔 Firestore 업로드 가능하게 처리"""
    if pd.isna(value):
        return None
    return value


def main():
    if not CSV_PATH.exists():
        print(f"CSV 파일이 없습니다: {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"CSV 로드 완료: {len(df)}행, {len(df.columns)}열")

    batch = db.batch()
    batch_count = 0
    total_uploaded = 0

    for idx, row in df.iterrows():
        data = {col: clean_value(row[col]) for col in df.columns}

        # 문서 ID 자동 생성
        doc_ref = db.collection(COLLECTION_NAME).document()
        batch.set(doc_ref, data)
        batch_count += 1

        # Firestore batch는 너무 크게 보내지 않도록 나눠서 업로드
        if batch_count >= 400:
            batch.commit()
            total_uploaded += batch_count
            print(f"{total_uploaded}개 업로드 완료")
            batch = db.batch()
            batch_count = 0

    # 남은 데이터 커밋
    if batch_count > 0:
        batch.commit()
        total_uploaded += batch_count

    print(f"업로드 완료! 총 {total_uploaded}개 문서가 '{COLLECTION_NAME}' 컬렉션에 저장되었습니다.")


if __name__ == "__main__":
    main()
