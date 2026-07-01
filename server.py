import math
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_brain import get_ai_decision
import data_collector
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
def analyze_stock(ticker: str, strategy: str = "volatility"):
    stock_code, stock_name = stock_utils.get_stock_info(ticker)

    if not stock_code:
        return {"status": "error", "message": f"'{ticker}' 종목을 찾을 수 없습니다."}

    # 💡 마스터 사전을 거쳐 나온 '주식코드(stock_code)'를 기준으로 국내/해외 판별!
    clean_code = str(stock_code).strip()

    if clean_code.isdigit() and len(clean_code) == 6:
        # 🇰🇷 국내 주식이면 6자리 숫자이므로 .KS 접미사 부착
        yahoo_ticker = f"{clean_code}.KS"
    else:
        # 🇺🇸 미국 주식이면 영문 티커이므로 그대로 대문자화 (TSLA, NVDA 등)
        yahoo_ticker = clean_code.upper()

    print(f"\n🚀 [{stock_name}({stock_code})] 하이브리드 분석 시작...")
    print(f"   🎯 최종 결정된 야후 차트 심볼: {yahoo_ticker}")

    # 구별된 yahoo_ticker와 stock_code가 각각의 수집 엔진으로 전달됩니다.
    df = data_collector.get_yahoo_chart(yahoo_ticker)
    realtime_data = data_collector.get_naver_realtime(stock_code)
    news_titles = data_collector.get_naver_news(stock_code)

    if df is None or df.empty:
        return {"status": "error", "message": "차트 데이터를 불러올 수 없습니다."}

    final_context = ""
    # --- [가격 결정 로직 교정 구역] ---
    close_col = 'Close' if 'Close' in df.columns else 'close'

    # 기본값은 차트의 가장 최신 종가로 안전하게 잡아둡니다 (예: 353.32)
    current_price = float(df[close_col].iloc[-1])

    # 💡 [핵심 교정]: realtime_data가 있고, '실제 가격이 0보다 클 때만' 덮어씁니다!
    if realtime_data and realtime_data.get('price', 0) > 0:
        try:
            price_str = str(realtime_data['price']).replace(',', '')
            current_price = float(price_str)

            final_context += (
                f"[실시간 시장 데이터 (최우선 기준)]\n"
                f"현재가: {realtime_data['price']}원/달러\n"
                f"등락률: {realtime_data['rate']}%\n"
                f"거래량: {realtime_data['vol']}\n"
                f"상태: {realtime_data['status']}\n\n"
            )
        except Exception:
            # 혹시나 형변환 에러가 나면 0으로 만들지 않고 차트 종가(기본값)를 유지합니다.
            pass
    else:
        # 미국 주식 등 실시간 피드가 0을 뱉으면 이리로 와서 안전하게 차트 종가를 바인딩합니다.
        final_context += f"[실시간 데이터 지연] 차트 종가({current_price})를 기준으로 분석합니다.\n\n"

    final_context += "[최신 뉴스 헤드라인]\n"
    if news_titles:
        for t in news_titles:
            final_context += f"- {t}\n"
    else:
        final_context += "특이 뉴스 없음.\n"

    print("🤖 Gemini AI 종합 판단 요청 중...")

    ai_result = get_ai_decision(
        ticker=stock_name,
        df=df,
        news_summary=final_context,
        strategy_type=strategy
    )

    rsi_val = 0.0
    macd_val = 0.0

    if df is not None and not df.empty:
        import pandas_ta_classic as ta
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)

        rsi_cols = [c for c in df.columns if c.lower().startswith('rsi')]
        macd_cols = [c for c in df.columns if
                     c.lower().startswith('macd_') and not c.lower().endswith('h') and not c.lower().endswith('s')]

        if rsi_cols:
            rsi_val = float(df[rsi_cols[0]].iloc[-1])

        if macd_cols:
            macd_val = float(df[macd_cols[0]].iloc[-1])

        if math.isnan(rsi_val): rsi_val = 0.0
        if math.isnan(macd_val): macd_val = 0.0

    return {
        "status": "success",
        "name": stock_name,
        "code": stock_code,
        "current_price": current_price,
        "signal": ai_result.get('decision', 'HOLD').lower(),
        "rsi": rsi_val,
        "macd": macd_val,
        "summary": ai_result.get('reason', '분석 이유를 가져오지 못했습니다.')
    }


@app.get("/top_stocks")
def get_top_stocks():
    try:
        url = "https://finance.naver.com/sise/lastsearch2.naver"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "lxml")

        items = soup.select("table.type_5 tr a.tltle")
        top_20 = [item.text for item in items[:20]]
        return {"top_stocks": top_20}

    except Exception as e:
        return {"top_stocks": ["삼성전자", "SK하이닉스", "카카오", "NAVER", "현대차"]}