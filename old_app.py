import streamlit as st
import requests

st.title("국가별 무역 분석 AI 챗봇")

API_URL = "http://127.0.0.1:8000/chat"

question = st.text_input("질문을 입력하세요")

if st.button("전송"):
    if not question.strip():
        st.warning("질문을 입력해주세요.")
    else:
        try:
            response = requests.post(
                API_URL,
                json={"question": question},
                timeout=10
            )

            st.write("요청 URL:", API_URL)
            st.write("상태코드:", response.status_code)
            st.write("응답 내용:", response.text)

            if response.status_code == 200:
                result = response.json()
                st.success(result.get("answer", "answer 값이 없습니다."))
            else:
                st.error(f"API 오류: {response.status_code}")

        except Exception as e:
            st.error(f"오류 발생: {e}")