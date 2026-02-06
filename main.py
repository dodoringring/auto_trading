from ai_brain import get_ai_decision
import data_collector
import sys


# 한글 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# =========================================================
# ⚙️ 설정 (여기를 수정하여 종목 변경)
# =========================================================
# TICKER = "000660.KS"    # 야후 파이낸스용 (SK하이닉스)
TICKER = "000660.KS"    # 야후 파이낸스용 (hpsp)
NAVER_CODE = "000660"   # 네이버 파이낸스용
STOCK_NAME = "SK하이닉스"

# 사용하고 싶은 전략을 여기서 고르세요!
# 1. "volatility" (변동성 돌파 - 단타용)
# 2. "goldencross" (골든크로스 - 추세용)
# 3. "rsi_bollinger" (역추세 - 줍줍용)
MY_STRATEGY = "volatility"

print("\n" + "="*60)
print(f"🚀 [{STOCK_NAME}] 하이브리드 자동매매 시스템 가동")
print("="*60)

# =========================================================
# 🚀 메인 로직 실행
# =========================================================

# [Step 1] 야후 파이낸스 차트 데이터 (기술적 분석용)
print(f"\n[Step 1] 과거 차트 데이터 분석 ({TICKER})...")
try:
    df = data_collector.get_yahoo_chart(TICKER)


    if df is None:
        print("❌ 데이터 다운로드 실패 (빈 데이터)")
        exit()



except Exception as e:
    print(f"❌ 차트 처리 중 오류: {e}")
    exit()


# [Step 2 & 3] 실시간 데이터 및 뉴스 수집 (함수 호출)
realtime_data = data_collector.get_naver_realtime(NAVER_CODE)
news_titles = data_collector.get_naver_news(NAVER_CODE)


# [Step 4] AI에게 보낼 통합 데이터 구성
# 여기가 제일 중요합니다. AI에게 차트+실시간+뉴스를 섞어서 줍니다.
final_context = ""

# 1. 실시간 시세 정보 입력
if realtime_data:
    print(f"   ⚡ 실시간 현재가: {realtime_data['price']:,}원 ({realtime_data['rate']}%)")
    final_context += (
        f"[실시간 시장 데이터 (최우선 기준)]\n"
        f"현재가: {realtime_data['price']}원\n"
        f"등락률: {realtime_data['rate']}%\n"
        f"거래량: {realtime_data['vol']}\n"
        f"상태: {realtime_data['status']}\n"
        f"주의: 위 데이터는 1초 단위 실시간 데이터입니다. 차트의 종가보다 이것을 우선하세요.\n\n"
    )
else:
    print("   ⚠️ 실시간 데이터를 가져오지 못해 차트 종가로 대체합니다.")
    final_context += "[실시간 데이터 조회 실패. 차트 데이터만 참고하세요.]\n\n"

# 2. 뉴스 정보 입력
final_context += "[최신 뉴스 헤드라인]\n"
if news_titles:
    for t in news_titles:
        final_context += f"- {t}\n"
        print(f"   📰 {t}")
else:
    final_context += "특이 뉴스 없음.\n"


# [Step 5] AI 분석 요청
print(f"\n[Step 4] Gemini AI 종합 판단 요청...")
ai_result = get_ai_decision(df, final_context, strategy_type=MY_STRATEGY)


# [Step 6] 최종 결과 출력
print("\n" + "="*60)
print(f"🤖 AI {STOCK_NAME} 분석 리포트")
print("="*60)
if realtime_data:
    print(f"💰 기 준 가 : {realtime_data['price']:,}원 (실시간)")
else:
    print(f"💰 기 준 가 : {df['Close'].iloc[-1]:,.0f}원 (종가)")
print("-" * 60)
print(f"📊 결    과 : {ai_result.get('decision', 'ERROR').upper()}")
print(f"📝 상세이유 : {ai_result.get('reason', '이유 없음')}")
print("="*60)