from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import data_collector
from ai_brain import get_ai_decision
import math
import stock_utils
import requests
from bs4 import BeautifulSoup

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
    ai_result = get_ai_decision(df, final_context, strategy_type=strategy)

    # 🌟 2. 데이터프레임(df)이 정상적으로 있다면 지표 계산 및 추출!
    if df is not None and not df.empty:
        # 혹시 계산이 안 되어 있을까 봐 여기서 확실하게 한 번 더 계산 (append=True)
        import pandas_ta_classic as ta
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)

        # 선생님이 찾으신 완벽한 '안전하게 컬럼 찾기' 로직 적용!
        rsi_cols = [c for c in df.columns if c.lower().startswith('rsi')]
        macd_cols = [c for c in df.columns if
                     c.lower().startswith('macd_') and not c.lower().endswith('h') and not c.lower().endswith('s')]

        # 값이 있으면 최신 값(iloc[-1])을 가져옵니다.
        if rsi_cols:
            rsi_val = float(df[rsi_cols[0]].iloc[-1])
        if macd_cols:
            macd_val = float(df[macd_cols[0]].iloc[-1])

        # 혹시라도 값이 NaN(결측치)이면 0으로 처리
        import math
        if math.isnan(rsi_val): rsi_val = 0
        if math.isnan(macd_val): macd_val = 0

    return {
        "status": "success",
        # 🌟 바뀐 부분: 이름과 코드를 각각 보냅니다.
        "name": stock_name,
        "code": naver_code,
        "current_price": current_price,
        "signal": ai_result.get('decision', 'HOLD').lower(),
        "rsi": rsi_val,
        "macd": macd_val,  # 🌟 추가된 부분: MACD 값 프론트로 보내기!
        "summary": ai_result.get('reason', '분석 이유를 가져오지 못했습니다.')
    }


@app.get("/top_stocks")
def get_top_stocks():
    try:
        # 네이버 금융 '검색 상위 종목' 페이지
        url = "https://finance.naver.com/sise/lastsearch2.naver"
        # 봇(Bot)으로 오해받지 않게 사람인 척하는 헤더
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "lxml")

        # 종목명 태그 찾기
        items = soup.select("table.type_5 tr a.tltle")

        # 상위 20개만 리스트로 묶기
        top_20 = [item.text for item in items[:20]]
        return {"top_stocks": top_20}

    except Exception as e:
        # 혹시 크롤링에 실패하면 기본 종목들을 내려주도록 방어 코드 작성
        return {"top_stocks": ["삼성전자", "SK하이닉스", "카카오", "NAVER", "현대차"]}