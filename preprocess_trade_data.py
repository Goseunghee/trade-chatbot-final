import re
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "trade_data_clean.csv"


def find_csv_file():
    candidates = []

    candidates.extend(BASE_DIR.glob("*.csv"))

    raw_dir = BASE_DIR / "data" / "raw"
    if raw_dir.exists():
        candidates.extend(raw_dir.glob("*.csv"))

    candidates = [f for f in candidates if f.is_file()]

    if not candidates:
        raise FileNotFoundError(
            "CSV 파일을 찾지 못했습니다. 프로젝트 폴더 또는 data/raw 폴더에 CSV를 넣어주세요."
        )

    candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    print("\n[찾은 CSV 파일 목록]")
    for f in candidates[:10]:
        print("-", f)

    selected = candidates[0]
    print("\n[선택된 파일]", selected)
    return selected


def read_korean_csv(path: Path) -> pd.DataFrame:
    encodings = ["cp949", "euc-kr", "utf-8-sig", "utf-8"]

    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc)
            print(f"[성공] encoding={enc}")
            return df
        except Exception as e:
            print(f"[실패] encoding={enc} -> {e}")

    raise ValueError("파일 인코딩을 읽지 못했습니다.")


def map_indicator(text: str):
    text = str(text).strip()

    if "수출" in text:
        return "export_value"
    elif "수입" in text:
        return "import_value"
    elif "무역수지" in text:
        return "trade_balance"
    return None


def main():
    print("현재 작업 폴더:", BASE_DIR)

    raw_path = find_csv_file()
    print("원본 파일 존재 여부:", raw_path.exists())

    df = read_korean_csv(raw_path)

    print("\n[원본 컬럼]")
    print(df.columns.tolist()[:10])

    df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed")]
    df = df.dropna(axis=1, how="all")

    if len(df.columns) < 4:
        raise ValueError("컬럼 수가 예상보다 적습니다. 원본 파일 구조를 다시 확인하세요.")

    df = df.rename(columns={
        df.columns[0]: "country",
        df.columns[1]: "indicator",
        df.columns[2]: "unit",
    })

    df["country"] = df["country"].astype(str).str.strip()
    df["indicator"] = df["indicator"].astype(str).str.strip()
    df["unit"] = df["unit"].astype(str).str.strip()

    date_cols = [col for col in df.columns if re.search(r"\d{4}\.\d{2}", str(col))]

    print("\n[날짜 컬럼 개수]", len(date_cols))
    print("[날짜 컬럼 예시]", date_cols[:5])

    if not date_cols:
        raise ValueError("월 컬럼을 찾지 못했습니다. 컬럼명을 확인하세요.")

    long_df = df.melt(
        id_vars=["country", "indicator", "unit"],
        value_vars=date_cols,
        var_name="year_month_raw",
        value_name="value"
    )

    long_df["year_month"] = (
        long_df["year_month_raw"]
        .astype(str)
        .str.extract(r"(\d{4}\.\d{2})")[0]
        .str.replace(".", "-", regex=False)
    )

    long_df["date"] = pd.to_datetime(long_df["year_month"] + "-01", errors="coerce")

    long_df["value"] = pd.to_numeric(
        long_df["value"].astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    )

    long_df["indicator_key"] = long_df["indicator"].apply(map_indicator)

    long_df = long_df.dropna(subset=["country", "year_month", "date", "indicator_key"])

    clean_df = long_df.pivot_table(
        index=["country", "date", "year_month"],
        columns="indicator_key",
        values="value",
        aggfunc="sum"
    ).reset_index()

    clean_df.columns.name = None

    for col in ["export_value", "import_value", "trade_balance"]:
        if col not in clean_df.columns:
            clean_df[col] = 0

    for col in ["export_value", "import_value", "trade_balance"]:
        clean_df[col] = clean_df[col].fillna(0).astype(int)

    clean_df = clean_df.sort_values(["country", "date"]).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("\n[전처리 완료]")
    print("저장 경로:", OUTPUT_PATH)
    print("\n[샘플]")
    print(clean_df.head())
    print("\n[국가 샘플]")
    print(clean_df["country"].dropna().unique()[:20])
    print("\n[전체 행 수]")
    print(len(clean_df))


if __name__ == "__main__":
    main()