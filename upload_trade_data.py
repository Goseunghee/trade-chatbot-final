import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# CSV 읽기
df = pd.read_csv("trade_data_clean.csv")

print("행 개수:", len(df))
print("컬럼:", df.columns.tolist())

# NaN -> None 변환
df = df.where(pd.notnull(df), None)

batch = db.batch()
count = 0
batch_count = 0

for idx, row in df.iterrows():
    doc_ref = db.collection("trade_data").document(str(idx))
    batch.set(doc_ref, row.to_dict())
    count += 1
    batch_count += 1

    # Firestore batch는 500개 단위 권장
    if batch_count == 500:
        batch.commit()
        print(f"{count}개 업로드 완료")
        batch = db.batch()
        batch_count = 0

# 남은 것 commit
if batch_count > 0:
    batch.commit()
    print(f"{count}개 업로드 완료")

print("업로드 완료!")