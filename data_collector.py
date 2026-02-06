import re

import yfinance as yf
import requests
from bs4 import BeautifulSoup

def get_yahoo_chart(ticker, period="1y"):
    """
    야후 파이낸스에서 주가 데이터 가져오기
    ticker: 종목코드 (예: '005930.KS')
    """
    print(f"   📥 [Yahoo] {ticker} 차트 데이터 다운로드 중...")
    try:
        # 야후 데이터 다운로드
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)

        # 데이터가 비어있으면 None 반환
        if df.empty:
            print("   ⚠️ [Yahoo] 데이터가 비어있습니다.")
            return None

        # 컬럼 이름 정리 (소문자로 통일)
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]

        # 필수 컬럼 확인
        if 'close' not in df.columns:
            # 가끔 야후가 'Adj Close'만 줄 때가 있음
            if 'adj close' in df.columns:
                df['close'] = df['adj close']
            else:
                return None
        # print(f"   @@ df: {df}")
        return df

    except Exception as e:
        print(f"   ❌ [Yahoo] 에러 발생: {e}")

        return None
# =========================================================
# 1. ⚡ 네이버 실시간 시세 (API)
# =========================================================
def get_naver_realtime(code):

    # --- [시도 1] 모바일 앱 API ---
    try:
        # ★ 수정된 부분: basic -> price?count=1 (오늘 날짜 데이터 1개만 요청)
        url = f"https://m.stock.naver.com/api/stock/{code}/price?count=1&page=1"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile)',
            'Referer': 'https://m.stock.naver.com/'
        }

        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code == 200:
            data_list = response.json()

            # 리스트 형태이므로 첫 번째([0]) 데이터가 오늘(최신) 데이터임
            if not data_list:
                raise Exception("데이터 리스트 비어있음")

            today_data = data_list[0]

            # API 키 값 확인 (closePrice, tradingVolume)
            return {
                'price': int(today_data['closePrice'].replace(',', '')),
                'rate': float(today_data['fluctuationsRatio']),
                # ★ 여기가 핵심: 'tradingVolume' 키를 사용
                'vol': int(today_data['tradingVolume'].replace(',', '')),
                'status': 'OPEN', # API는 장 상태를 안 주지만 데이터가 있으면 OPEN 취급
                'method': 'Mobile Price API'
            }
    except Exception as e:
        print(f"   ⚠️ Method A 실패 ({e}), Method B로 전환합니다.")

    # --- [시도 2] PC 웹 HTML 파싱 (최후의 수단) ---
    try:
        print(f"   🔄 Method B 시도 중 (HTML Scraping)...")
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')

        no_today = soup.select_one('.no_today .blind')
        if no_today:
            price = int(no_today.text.replace(',', ''))

            # 등락률 안전하게 추출
            rate = 0.0
            exday = soup.select_one('.no_exday')
            if exday:
                rate_text = exday.get_text().strip()
                match = re.search(r'([+-]?\d+\.\d+)%', rate_text)
                if match:
                    rate = float(match.group(1))
                    if soup.select_one('.ico_down') and rate > 0:
                        rate = -rate

            # ★ [핵심 수정] 거래량(vol)을 0으로 두지 않고 크롤링함
            vol = 0
            # 네이버 페이지 구조상 거래량은 .no_info 클래스 안에 숨어있음
            vol_tag = soup.select_one('.no_info .blind')
            if vol_tag:
                vol = int(vol_tag.get_text().replace(',', ''))

            return {
                'price': price,
                'rate': rate,
                'vol': vol,  # 이제 0이 아니라 실제 값이 들어감!
                'status': 'OPEN',
                'method': 'HTML Parsing'
            }

    except Exception as e:
        print(f"   ❌ 모든 방법 실패: {e}")
        return None

# =========================================================
# 2. 📰 네이버 뉴스 크롤링
# =========================================================
def get_naver_news(code):
    print(f"[Step 3] 네이버 뉴스 수집 중...")
    url = f"https://finance.naver.com/item/news_news.naver?code={code}"
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': f'https://finance.naver.com/item/main.naver?code={code}'
    }

    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'euc-kr' # 인코딩 필수
        soup = BeautifulSoup(response.text, 'html.parser')

        titles = soup.select('a.tit')

        news_list = []
        for link in titles[:5]: # 상위 5개만
            title = link.get_text().strip()
            if title:
                news_list.append(title)
        return news_list

    except Exception as e:
        print(f"   ⚠️ 뉴스 수집 실패: {e}")
        return []
