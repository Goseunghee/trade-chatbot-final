import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent.parent
cred_path = BASE_DIR / "serviceAccountKey.json"

if not cred_path.exists():
    raise FileNotFoundError(f"Firebase 키 파일 없음: {cred_path}")

if not firebase_admin._apps:
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred)

db = firestore.client()


def save_chat_log(question: str, result: dict) -> bool:
    try:
        doc = {
            "question": question,
            "intent": result.get("intent"),
            "answer": result.get("answer"),
            "country": result.get("country"),
            "year_month": result.get("year_month"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        db.collection("chat_logs").add(doc)
        return True

    except Exception as e:
        print(f"[Firestore 저장 실패] {e}")
        return False