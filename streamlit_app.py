import streamlit as st
import requests

# FastAPI 백엔드 주소
API_URL = "http://127.0.0.1:8000/ask"

st.set_page_config(
    page_title="무역 데이터 챗봇",
    page_icon="🌍",
    layout="centered"
)

st.title("🌍 무역 데이터 챗봇")
st.caption("국가별 수출, 수입, 무역수지를 자연어로 질문해보세요.")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 사이드바
with st.sidebar:
    st.header("사용 예시")
    st.write("- 미국 최신 무역수지 알려줘")
    st.write("- 한국 최신 수출액 알려줘")
    st.write("- 일본 최근 무역 데이터 보여줘")

    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.rerun()

# 이전 대화 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and msg.get("data"):
            with st.expander("상세 데이터 보기"):
                st.json(msg["data"])

# 사용자 입력
user_input = st.chat_input("질문을 입력하세요...")

if user_input:
    # 사용자 메시지 저장
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("답변 생성 중..."):
            try:
                response = requests.post(
                    API_URL,
                    json={"question": user_input},
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()

                    answer = result.get("answer", "응답이 없습니다.")
                    data = result.get("data", {})
                    intent = result.get("intent", "")
                    firestore_saved = result.get("firestore_saved", False)

                    st.markdown(answer)
                    st.caption(
                        f"intent: {intent} | Firestore 저장: {'성공' if firestore_saved else '실패'}"
                    )

                    if data:
                        with st.expander("상세 데이터 보기"):
                            st.json(data)

                    # assistant 메시지 저장
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "data": data,
                        "intent": intent,
                        "firestore_saved": firestore_saved
                    })

                else:
                    error_msg = f"서버 오류: {response.status_code}"
                    st.error(error_msg)
                    st.text(response.text)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })

            except requests.exceptions.ConnectionError:
                msg = "FastAPI 서버에 연결할 수 없습니다. 먼저 백엔드를 실행해주세요."
                st.error(msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": msg
                })

            except requests.exceptions.Timeout:
                msg = "요청 시간이 초과되었습니다."
                st.error(msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": msg
                })

            except Exception as e:
                msg = f"오류 발생: {e}"
                st.error(msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": msg
                })