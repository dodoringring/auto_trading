from google import genai
import os
import json
import strategy

# ==========================================
# 🔑 API 키 확인
# ==========================================
# 1. 일단 컴퓨터 환경변수를 뒤져본다.
api_key = os.environ.get("GEMINI_API_KEY")

# 2. 만약 아무것도 없다면? (로컬)
if not api_key:
    import config
    api_key = config.GEMINI_API_KEY

def get_ai_decision(df, news_summary, strategy_type):
    print("\n[🔍 AI_BRAIN] AI 분석 모듈 진입")

    # 1. 기술적 전략(수학) 먼저 물어보기
    tech_signal = strategy.get_strategy_signal(df, strategy_type)
    chart_summary = strategy.get_chart_summary(df)

    print(f"   🤖 [전략 신호] {strategy_type} -> {tech_signal.upper()}")

    try:
        client = genai.Client(api_key)
    except Exception as e:
        print(f"❌ [AI 설정 오류] : {e}")
        return {"decision": "hold", "reason": "API 연결 실패"}

    print(f"[🔍 AI_BRAIN] AI에게 보낼 차트 요약 데이터:\n{chart_summary.strip()}")

    # 3. 프롬프트 작성
    prompt = f"""
    너는 냉철한 주식 투자 전문가야. 
    아래 정보를 바탕으로 매매를 결정해.

    [기술적 분석 전략의 의견]
    - 사용 전략: {strategy_type}
    - 전략 신호: {tech_signal.upper()}

    [시장 데이터]
    {chart_summary}

    [최근 뉴스]
    {news_summary}

    [미션]
    1. 기술적 분석 전략 의견과 시장 데이터, 최근 뉴스를 종합해서 상황을 분석해.
    2. 'buy'(매수), 'sell'(매도), 'hold'(관망) 중 하나를 선택해.
    3. 이유는 한 문장으로 짧게 설명해.
    4. 대답은 반드시 아래 JSON 형식으로만 해.
    {{
        "decision": "buy",
        "reason": "RSI가 낮고 호재가 있음"
    }}
    """

    # print("[🔍 AI_BRAIN] Gemini에게 질문 전송 중...")

    try:
        response = client.models.generate_content(
            # model="gemini-3-flash-preview",
            model="models/gemma-3-27b-it",

            contents=prompt,
            # config=types.GenerateContentConfig(
            #     response_mime_type="application/json" # JSON 강제 출력 설정
            # )
        )


        # ★ AI 답변 원본 로그 출력  ★
        # print(f"\n[🔍 AI_BRAIN] 📩 Gemini 원본 응답:\n{response.text}")

        # JSON 파싱
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)

        return result

    except Exception as e:
        print(f"❌ [AI_BRAIN Error] : {e}")
        return {"decision": "hold", "reason": f"AI 에러 발생: {e}"}