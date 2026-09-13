import json
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase 연결
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 현재 연결된 프로젝트 확인
with open("serviceAccountKey.json", "r", encoding="utf-8") as f:
    key = json.load(f)

print("현재 project_id:", key["project_id"])
print("-" * 50)

# 컬렉션 목록 출력
collections = list(db.collections())

if not collections:
    print("컬렉션이 없습니다.")
else:
    print("Firestore 컬렉션 목록:")
    for col in collections:
        print("-", col.id)