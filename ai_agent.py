import google.generativeai as genai
import json

# ==========================================
# 🔑 여기에 아까 받은 API 키를 붙여넣으세요!
# ==========================================
MY_API_KEY = "AIzaSyAoGKoN5k0wg7jwKKx6aYw6DcU76GYf8zY"  # 따옴표 안에 키를 넣으세요

def get_ai_decision(df, news_summary):
    """
    구글 Gemini에게 차트와 뉴스를 주고 매매 판단을 요청하는 함수
    """
    # 1. 구글 API 설정
    genai.configure(api_key=MY_API_KEY)

    model = genai.GenerativeModel('gemini-3-flash-preview')

    # 2. 가장 최근 데이터 정리
    current = df.iloc[-1]
    chart_data = f"""
    - 현재가: {current['close']}
    - RSI: {current['RSI']:.2f}
    - 5일선: {current['SMA5']:.0f} vs 20일선: {current['SMA20']:.0f}
    """

    # 3. AI에게 보낼 명령서 (프롬프트)
    prompt = f"""
    너는 냉철한 주식 투자 전문가야. 아래 데이터를 분석해서 매매 결정을 내려줘.

    [시장 데이터]
    {chart_data}

    [최근 뉴스]
    {news_summary}

    [미션]
    1. 데이터와 뉴스를 종합해서 상황을 분석해.
    2. 'buy'(매수), 'sell'(매도), 'hold'(관망) 중 하나를 선택해.
    3. 이유는 한 문장으로 짧게 설명해.
    4. 대답은 반드시 아래 JSON 형식으로만 해 (다른 말 섞지 마).
    {{
        "decision": "buy",
        "reason": "RSI가 낮고 호재가 있어서 진입 추천"
    }}
    """

    try:
        # 4. AI에게 질문 던지기
        response = model.generate_content(prompt)

        # 5. 대답 정리 (가끔 AI가 ```json 같은 걸 붙여서 떼어냄)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)
        return result

    except Exception as e:
        print(f"❌ AI 에러 발생: {e}")
        return {"decision": "hold", "reason": "AI 연결 실패로 관망"}