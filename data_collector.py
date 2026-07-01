import re
import xml.etree.ElementTree as ET
import yfinance as yf
import requests
from bs4 import BeautifulSoup


# =========================================================
# 📊 1. 야후 파이낸스 차트 다운로더 (국내/해외 완벽 대응)
# =========================================================
def get_yahoo_chart(ticker, period="1y"):
    """
    야후 파이낸스에서 주가 데이터 가져오기
    ticker: 국내 주식은 '005930.KS', 미국 주식은 'TSLA' 형태로 들어옵니다.
    """
    # 🌟 [보안 및 예외 가드] 종목 정보가 숫자로만 전달되거나 소문자로 들어왔을 때의 안전 분기
    clean_ticker = str(ticker).strip()
    if clean_ticker.isdigit() and len(clean_ticker) == 6:
        clean_ticker = f"{clean_ticker}.KS"
    else:
        clean_ticker = clean_ticker.upper()

    print(f"   📥 [Yahoo] {clean_ticker} 차트 데이터 다운로드 중...")
    try:
        df = yf.download(clean_ticker, period=period, interval="1d", progress=False, auto_adjust=True)

        if df.empty:
            print(f"   ⚠️ [Yahoo] {clean_ticker} 데이터가 비어있습니다.")
            return None

        # 컬럼 이름 정리 (Multi-index 방어용 소문자 통일)
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]

        # 필수 컬럼 확인 및 보정
        if 'close' not in df.columns:
            if 'adj close' in df.columns:
                df['close'] = df['adj close']
            else:
                return None
        return df

    except Exception as e:
        print(f"   ❌ [Yahoo] 에러 발생: {e}")
        return None


# =========================================================
# ⚡ 2. 실시간 시세 엔진 (국내: 네이버 API / 미국: 야후 인포)
# =========================================================
def get_naver_realtime(code):
    """
    실시간 시세 및 거래량 데이터 덤프
    code: 6자리 숫자(국내) 혹은 영문 티커(미국)
    """
    clean_code = str(code).strip()

    # 🇺🇸 [미국 주식 분기 가드] 영문 알파벳이 포함되어 있으면 네이버를 패스하고 야후 실시간으로 스위칭!
    if not clean_code.isdigit():
        print(f"   🇺🇸 [US Market] '{clean_code.upper()}' 미국 주식 실시간 시세를 야후 엔진에서 추출합니다.")
        try:
            ticker_obj = yf.Ticker(clean_code.upper())
            # fast_info 또는 history 최신값 조회를 통해 실시간 가격 정보를 고속 추출합니다.
            fast_info = ticker_obj.fast_info

            # 야후에서 제공하는 미국주식 당일 실시간 덤프 포맷팅
            return {
                'price': float(fast_info.get('last_price', 0)),
                'rate': float(fast_info.get('regular_market_previous_close', 0)),  # 변동률 연산 대안
                'vol': int(fast_info.get('last_volume', 0)),
                'status': 'OPEN',
                'method': 'Yahoo FastInfo API'
            }
        except Exception as e:
            print(f"   ❌ [Yahoo Realtime] 미국 주식 실시간 시세 로드 실패: {e}")
            return None

    # 🇰🇷 [국내 주식 로직] 기존 개발자님의 완벽한 2단계 크롤링 라인을 그대로 유지합니다.
    # --- [시도 1] 모바일 앱 API ---
    try:
        url = f"https://m.stock.naver.com/api/stock/{clean_code}/price?count=1&page=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile)',
            'Referer': 'https://m.stock.naver.com/'
        }
        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code == 200:
            data_list = response.json()
            if not data_list:
                raise Exception("데이터 리스트 비어있음")

            today_data = data_list[0]
            return {
                'price': int(today_data['closePrice'].replace(',', '')),
                'rate': float(today_data['fluctuationsRatio']),
                'vol': int(today_data['tradingVolume'].replace(',', '')),
                'status': 'OPEN',
                'method': 'Mobile Price API'
            }
    except Exception as e:
        print(f"   ⚠️ Method A 실패 ({e}), Method B로 전환합니다.")

    # --- [시도 2] PC 웹 HTML 파싱 (최후의 수단) ---
    try:
        print(f"   🔄 Method B 시도 중 (HTML Scraping)...")
        url = f"https://finance.naver.com/item/main.naver?code={clean_code}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')

        no_today = soup.select_one('.no_today .blind')
        if no_today:
            price = int(no_today.text.replace(',', ''))
            rate = 0.0
            exday = soup.select_one('.no_exday')
            if exday:
                rate_text = exday.get_text().strip()
                match = re.search(r'([+-]?\d+\.\d+)%', rate_text)
                if match:
                    rate = float(match.group(1))
                    if soup.select_one('.ico_down') and rate > 0:
                        rate = -rate

            vol = 0
            vol_tag = soup.select_one('.no_info .blind')
            if vol_tag:
                vol = int(vol_tag.get_text().replace(',', ''))

            return {
                'price': price,
                'rate': rate,
                'vol': vol,
                'status': 'OPEN',
                'method': 'HTML Parsing'
            }
    except Exception as e:
        print(f"   ❌ 모든 방법 실패: {e}")
        return None


# =========================================================
# 📰 3. 뉴스 데이터 수집기 (국내: 네이버 금융 / 미국: 구글 뉴스 RSS)
# =========================================================
def get_naver_news(code):
    """
    종목별 최신 뉴스 수집 헤드라인 5개 반환
    """
    clean_code = str(code).strip()

    # 🇺🇸 [미국 주식 분기 가드] 숫자가 아니라 영문 티커면 네이버 대신 구글 뉴스 RSS 공급 체인 가동
    if not clean_code.isdigit():
        ticker_upper = clean_code.upper()
        print(f"[Step 3] 미국 주식 전용 구글 뉴스 RSS 수집 중 ({ticker_upper})...")
        try:
            # 인베스팅닷컴 크롤링 우회 대안으로 퀀트판에서 가장 신뢰하는 구글 뉴스 오피셜 영문 피드 활용
            url = f"https://news.google.com/rss/search?q={ticker_upper}+stock&hl=en-US&gl=US&ceid=US:en"
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=5)

            root = ET.fromstring(r.text)
            news_list = []

            # 최신 뉴스 아이템 리스트 상위 5개 확보
            for item in root.findall(".//item")[:5]:
                title = item.find("title").text
                if title:
                    news_list.append(title)
            print(f"news_list{news_list}")
            return news_list
        except Exception as e:
            print(f"   ⚠️ 미국 RSS 뉴스 수집 실패: {e}")
            return [f"No recent news found for {ticker_upper}"]



    # 🇰🇷 [국내 주식 로직] 네이버 금융에서 cp949 인코딩으로 안전하게 뉴스 서칭
    print(f"[Step 3] 네이버 뉴스 수집 중...")
    url = f"https://finance.naver.com/item/news_news.naver?code={clean_code}"
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': f'https://finance.naver.com/item/main.naver?code={clean_code}'
    }

    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, 'html.parser')

        titles = soup.select('a.tit')
        news_list = []
        for link in titles[:5]:
            title = link.get_text().strip()
            if title:
                news_list.append(title)
        return news_list

    except Exception as e:
        print(f"   ⚠️ 국내 뉴스 수집 실패: {e}")
        return []