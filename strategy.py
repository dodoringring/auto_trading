import pandas_ta_classic  as ta

def get_strategy_signal(df, strategy_type="volatility"):
    """
    원하는 전략을 선택해서 매매 신호를 받는 함수
    :param df: 주식 데이터 (open, high, low, close 필수)
    :param strategy_type: 'volatility', 'goldencross', 'rsi_bollinger'
    """
    # 데이터 컬럼명 소문자로 정리 (Open -> open)
    df.columns = [c.lower() for c in df.columns]

    # ------------------------------------------------
    # 1. 래리 윌리엄스의 변동성 돌파 전략 (단타 추천)
    # ------------------------------------------------
    if strategy_type == "volatility":
        # 어제 데이터 가져오기 (마지막에서 두 번째)
        yesterday = df.iloc[-2]
        today = df.iloc[-1]

        # 변동폭 계산 (어제 고가 - 어제 저가)
        range_yesterday = yesterday['high'] - yesterday['low']

        # 매수 목표가 설정 (오늘 시가 + 변동폭 * 0.5)
        # k=0.5는 래리 윌리엄스가 추천한 황금 비율
        target_price = today['open'] + (range_yesterday * 0.5)

        print(f"[변동성돌파] 목표가: {target_price:.0f}원 | 현재가: {today['close']:.0f}원")

        # 현재가가 목표가를 뚫었으면 매수!
        if today['close'] >= target_price:
            return "buy"

    # ------------------------------------------------
    # 2. 이동평균선 골든크로스 (추세 추종)
    # ------------------------------------------------
    elif strategy_type == "goldencross":
        # ★ 수정: 이름을 직접 지정해서 넣습니다. (검색X)
        df['MY_SMA5'] = df.ta.sma(length=5)
        df['MY_SMA20'] = df.ta.sma(length=20)

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        # 값이 없으면(NaN) 0으로 처리
        curr_sma5 = curr.get('MY_SMA5', 0) or 0
        curr_sma20 = curr.get('MY_SMA20', 0) or 0
        prev_sma5 = prev.get('MY_SMA5', 0) or 0
        prev_sma20 = prev.get('MY_SMA20', 0) or 0

        print(f"   📐 [골든크로스] 5일: {curr_sma5:.0f} | 20일: {curr_sma20:.0f}")

        if prev_sma5 < prev_sma20 and curr_sma5 > curr_sma20:
            return "buy"
        elif prev_sma5 > prev_sma20 and curr_sma5 < curr_sma20:
            return "sell"

    # ------------------------------------------------
    # 3. RSI + 볼린저밴드 줍줍 전략 (역추세)
    # ------------------------------------------------
    elif strategy_type == "rsi_bollinger":
        # 지표 계산 (append=True로 df에 직접 추가)
        df.ta.rsi(length=14, append=True)
        df.ta.bbands(length=20, std=2, append=True)

        # ★ [에러 수정 부분] 컬럼 찾기 로직 강화
        # 대문자(BBL)든 소문자(bbl)든 상관없이 'bbl'로 시작하는 컬럼을 찾음
        lower_cols = [c for c in df.columns if c.lower().startswith('bbl')]
        rsi_cols = [c for c in df.columns if c.lower().startswith('rsi')]

        if not lower_cols or not rsi_cols:
            print("   ⚠️ 지표 계산 오류: 컬럼을 찾을 수 없습니다.")
            return "hold"

        lower_col = lower_cols[0] # BBL_20_2.0
        rsi_col = rsi_cols[0]     # RSI_14

        curr = df.iloc[-1]
        print(f"   📐 [역추세] RSI: {curr[rsi_col]:.1f} | 밴드하단: {curr[lower_col]:.0f}")

        if curr[rsi_col] < 30 and curr['close'] <= curr[lower_col]:
            return "buy"
        elif curr[rsi_col] > 70:
            return "sell"

    return "hold" # 아무 신호 없으면 관망

def get_chart_summary(df):
    """AI에게 보낼 데이터 요약 (보조지표 추가 계산)"""
    if df is None or len(df) < 20:
        return "데이터 부족으로 분석 불가"

    # AI 참고용 지표 계산 (이미 계산되어 있어도 덮어씀)
    df.ta.rsi(length=14, append=True)
    df.ta.macd(append=True)

    curr = df.iloc[-1]

    # 안전하게 컬럼 찾기 (대소문자 무시)
    rsi_col = [c for c in df.columns if c.lower().startswith('rsi')][0]
    macd_col = [c for c in df.columns if c.lower().startswith('macd_') and not c.lower().endswith('h') and not c.lower().endswith('s')][0]

    summary = f"""
    [기술적 지표 요약]
    - 현재가: {curr['close']:.0f}
    - RSI(14): {curr.get(rsi_col, 0):.2f}
    - MACD: {curr.get(macd_col, 0):.2f}
    """
    return summary