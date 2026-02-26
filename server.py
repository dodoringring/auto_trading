from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import data_collector
from ai_brain import get_ai_decision
import math
import stock_utils

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/analyze")
def analyze_stock(ticker: str = "삼성전자"):
    # 🌟 바뀐 부분: 코드와 이름을 둘 다 가져옵니다!
    naver_code, stock_name = stock_utils.get_stock_info(ticker)

    if not naver_code:
        return {"status": "error", "message": f"'{ticker}' 종목을 찾을 수 없습니다."}

    yahoo_ticker = naver_code + ".KS"

    print(f"\n🚀 [{stock_name}({naver_code})] 하이브리드 분석 시작...")

    df = data_collector.get_yahoo_chart(yahoo_ticker)
    realtime_data = data_collector.get_naver_realtime(naver_code)
    news_titles = data_collector.get_naver_news(naver_code)

    if df is None or df.empty:
        return {"status": "error", "message": "차트 데이터를 불러올 수 없습니다."}

    final_context = ""
    close_col = 'Close' if 'Close' in df.columns else 'close'
    current_price = float(df[close_col].iloc[-1])

    if realtime_data:
        price_str = str(realtime_data['price']).replace(',', '')
        current_price = float(price_str)

        final_context += (
            f"[실시간 시장 데이터 (최우선 기준)]\n"
            f"현재가: {realtime_data['price']}원\n"
            f"등락률: {realtime_data['rate']}%\n"
            f"거래량: {realtime_data['vol']}\n"
            f"상태: {realtime_data['status']}\n"
            f"주의: 차트의 종가보다 이것을 우선하세요.\n\n"
        )
    else:
        final_context += "[실시간 데이터 조회 실패. 차트 데이터만 참고하세요.]\n\n"

    final_context += "[최신 뉴스 헤드라인]\n"
    if news_titles:
        for t in news_titles:
            final_context += f"- {t}\n"
    else:
        final_context += "특이 뉴스 없음.\n"

    print("🤖 Gemini AI 종합 판단 요청 중...")
    ai_result = get_ai_decision(df, final_context, strategy_type="volatility")

    rsi_val = 0
    if 'RSI_14' in df.columns:
        rsi_val = float(df['RSI_14'].iloc[-1])
    if math.isnan(rsi_val):
        rsi_val = 0

    return {
        "status": "success",
        # 🌟 바뀐 부분: 이름과 코드를 각각 보냅니다.
        "name": stock_name,
        "code": naver_code,
        "current_price": current_price,
        "signal": ai_result.get('decision', 'HOLD').lower(),
        "rsi": rsi_val,
        "summary": ai_result.get('reason', '분석 이유를 가져오지 못했습니다.')
    }