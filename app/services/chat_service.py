import re
from app.services.trade_service import (
    get_all_countries,
    get_latest_trade_data,
    get_country_monthly_data,
    get_trade_balance_ranking,
)


def format_number(value):
    return f"{int(value):,}"


def extract_year_month(question: str):
    match = re.search(r"(20\d{2})[\-\.년\s]+(0?[1-9]|1[0-2])", question)
    if match:
        year = match.group(1)
        month = int(match.group(2))
        return f"{year}-{month:02d}"
    return None


def extract_limit(question: str):
    match = re.search(r"(\d+)\s*개", question)
    if match:
        return int(match.group(1))
    return 5


def extract_country(question: str):
    countries = sorted(get_all_countries(), key=len, reverse=True)

    for country in countries:
        if country in question:
            return country

    return None


def answer_question(question: str):
    question = question.strip()
    year_month = extract_year_month(question)
    limit = extract_limit(question)
    country = extract_country(question)

    # 1. 순위 질문
    if any(keyword in question for keyword in ["순위", "상위", "하위"]):
        if any(keyword in question for keyword in ["적자", "하위", "낮은"]):
            order = "asc"
            rank_text = "무역수지 적자 상위"
        else:
            order = "desc"
            rank_text = "무역수지 흑자 상위"

        result = get_trade_balance_ranking(
            year_month=year_month,
            limit=limit,
            order=order
        )

        if not result:
            return {
                "intent": "ranking",
                "question": question,
                "answer": "해당 월의 순위 데이터를 찾을 수 없습니다.",
                "data": None,
                "firestore_saved": False
            }

        lines = [f"{result['year_month']} {rank_text} {limit}개국입니다."]
        for i, row in enumerate(result["results"], start=1):
            lines.append(
                f"{i}. {row['country']} - 무역수지 {format_number(row['trade_balance'])}"
            )

        return {
            "intent": "ranking",
            "question": question,
            "answer": "\n".join(lines),
            "data": result,
            "firestore_saved": False
        }

    # 2. 국가별 월별 데이터 질문
    if country and any(keyword in question for keyword in ["월별", "추이", "변화"]):
        data = get_country_monthly_data(country)

        if not data:
            return {
                "intent": "monthly",
                "question": question,
                "answer": f"{country}의 월별 데이터를 찾을 수 없습니다.",
                "data": None,
                "firestore_saved": False
            }

        return {
            "intent": "monthly",
            "question": question,
            "answer": f"{country}의 월별 데이터를 조회했습니다.",
            "data": {
                "country": country,
                "count": len(data),
                "monthly_data": data
            },
            "firestore_saved": False
        }

    # 3. 국가별 최신 데이터 질문
    if country:
        latest = get_latest_trade_data(country)

        if not latest:
            return {
                "intent": "latest_trade",
                "question": question,
                "answer": f"{country}의 최신 데이터를 찾을 수 없습니다.",
                "data": None,
                "firestore_saved": False
            }

        answer = (
            f"{country}의 최신 데이터는 {latest['year_month']} 기준입니다. "
            f"수출은 {format_number(latest['export_value'])}, "
            f"수입은 {format_number(latest['import_value'])}, "
            f"무역수지는 {format_number(latest['trade_balance'])}입니다."
        )

        return {
            "intent": "latest_trade",
            "question": question,
            "answer": answer,
            "data": latest,
            "firestore_saved": False
        }

    # 4. 국가 목록 질문
    if any(keyword in question for keyword in ["국가 목록", "나라 목록", "국가 리스트"]):
        countries = get_all_countries()
        return {
            "intent": "country_list",
            "question": question,
            "answer": f"총 {len(countries)}개 국가가 있습니다.",
            "data": countries,
            "firestore_saved": False
        }

    # 5. 이해 못한 질문
    return {
        "intent": "unknown",
        "question": question,
        "answer": "질문을 이해하지 못했습니다. 예: '중국 최근 무역수지 알려줘', '2026년 7월 흑자 상위 5개국'",
        "data": None,
        "firestore_saved": False
    }