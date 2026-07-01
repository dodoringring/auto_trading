from google import genai
import os
import json
import time  # ⏳ 캐시 시간 계산을 위해 추가
import strategy

# ==========================================
# 🔑 API 키 확인
# ==========================================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    import config
    api_key = config.GEMINI_API_KEY

# ==========================================
# ⚡ 10분 서버 메모리 캐시 저장소 선언
# ==========================================
AI_RESPONSE_CACHE = {}
CACHE_DURATION = 300  # 10분 = 600초


# 🌟 [수정] 함수의 첫 번째 인자로 ticker(종목명)를 받도록 확장합니다!
def get_ai_decision(ticker, df, news_summary, strategy_type):
    global AI_RESPONSE_CACHE
    current_time = time.time()

    print(f"\n[🔍 AI_BRAIN] {ticker} AI 분석 모듈 진입")

    # 1. 기술적 전략(수학) 먼저 물어보기
    tech_signal = strategy.get_strategy_signal(df, strategy_type)
    chart_summary = strategy.get_chart_summary(df)

    print(f"   🤖 [전략 신호] {strategy_type} -> {tech_signal.upper()}")
    print(f"[🔍 AI_BRAIN] AI에게 보낼 차트 요약 데이터:\n{chart_summary.strip()}")

    # 💡 [핵심 수정] 불안정한 현재가 추출 대신, '종목명'과 '전략타입'을 엮어 완벽한 고유 키를 만듭니다!
    clean_ticker = str(ticker).strip().upper()
    cache_key = f"{clean_ticker}_{strategy_type}"

    # 2️⃣ 만약 10분 이내에 '동일 종목'의 '동일 전략'으로 요청이 들어왔다면?
    if cache_key in AI_RESPONSE_CACHE:
        cache_data = AI_RESPONSE_CACHE[cache_key]
        if current_time < cache_data["expire_at"]:
            print(f"⚡ [Cache Hit] '{ticker}'는 10분 이내 분석한 기록이 있어 캐시에서 즉시 반환합니다!")
            return cache_data["result"]
        else:
            print(f"⏳ [Cache Expired] '{ticker}'의 캐시가 만료되었습니다. 새로 갱신합니다.")
            del AI_RESPONSE_CACHE[cache_key]

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"❌ [AI 설정 오류] : {e}")
        return {"decision": "hold", "reason": "API 연결 실패"}

    # 3. 프롬프트 작성 (종목명 정보를 추가하여 AI가 더 정확히 인지하도록 보완)
    prompt = f"""
    너는 냉철한 주식 투자 전문가야. 
    아래 정보를 바탕으로 [{ticker}] 종목의 매매를 결정해.

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

    try:
        response = client.models.generate_content(
            # model="gemini-3.5-flash",Gemini 3.1 Flash Lite
            model="gemini-3.1-flash-lite",
            contents=prompt,
        )

        # JSON 파싱
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)

        # 4️⃣ 성공적으로 분석된 결과를 10분 동안 해당 종목 전용 방에 락(Lock) 걸어둡니다.
        AI_RESPONSE_CACHE[cache_key] = {
            "expire_at": current_time + CACHE_DURATION,
            "result": result
        }
        print(f"✅ [Cache Saved] '{ticker}'의 신규 분석 결과를 10분간 캐시에 저장했습니다.")

        return result

    except Exception as e:
        print(f"❌ [AI_BRAIN Error] : {e}")
        return {"decision": "hold", "reason": f"AI 에러 발생: {e}"}