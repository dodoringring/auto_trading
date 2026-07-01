import os
import json
import urllib.parse
from pathlib import Path

MASTER_FILE = "global_stock_master.json"
STOCK_MASTER = {}

# 📂 수동으로 다운로드한 한투 mst/cod 파일들이 위치할 폴더 경로
MST_DIR = Path("mst_files")


def init_stock_master():
    """
    한투 국내 마스터(.mst)의 바이트 규격과 해외 마스터(.cod)의 탭(Tab) 분할 규격을
    모두 정확하게 인지하여 디코딩 에러 없이 완벽한 통합 사전을 구축합니다.
    """
    global STOCK_MASTER

    # 1️⃣ 이미 사전 파일이 잘 빌드되어 있다면 초고속 패스!
    if os.path.exists(MASTER_FILE):
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                STOCK_MASTER = json.load(f)
            if STOCK_MASTER and len(STOCK_MASTER) > 1000:  # 국내외 포함이므로 기준치 상향
                print(f"💾 [STOCK_MASTER] >>> 로컬 사전 파일에서 {len(STOCK_MASTER)}개 종목을 즉시 로드했습니다.")
                return
        except Exception:
            pass

    print(f"📂 [최초 1회 실행] 수동 마스터 폴더 '{MST_DIR}' 내부 한투 데이터 스캔 중...")
    master_data = {}
    file_count = 0

    # -------------------------------------------------------------------------
    # 🇰🇷 1구역: 국내 주식 마스터 파일 파싱 (.mst 고정 바이트 규격)
    # -------------------------------------------------------------------------
    kr_files = ["kospi_code.mst", "kosdaq_code.mst"]
    for file_name in kr_files:
        file_path = MST_DIR / file_name
        if file_path.exists():
            file_count += 1
            print(f"📄 [STOCK_MASTER] >>> 국내 마스터 발견: '{file_name}' 파싱 시작...")
            try:
                with open(file_path, "rb") as f:
                    for line in f:
                        if len(line) >= 61:
                            raw_code = line[0:9].decode('cp949', errors='ignore').strip()
                            code = raw_code[-6:] if len(raw_code) >= 6 else raw_code.zfill(6)
                            name = line[21:61].decode('cp949', errors='ignore').strip()

                            if code.isdigit() and len(code) == 6 and name:
                                clean_name = name.lower().replace(" ", "")
                                master_data[clean_name] = {"code": code, "name": name}
            except Exception as e:
                print(f"⚠️ 국내 파일 '{file_name}' 처리 중 오류: {e}")

    # -------------------------------------------------------------------------
    # 🇺🇸 2구역: 해외 주식 마스터 파일 파싱 (NASMST.COD 탭 분할 규격)
    # -------------------------------------------------------------------------
    if MST_DIR.exists():
        for p in MST_DIR.glob("*"):
            if p.name.upper() == "NASMST.COD":
                file_count += 1
                print(f"📄 [STOCK_MASTER] >>> 해외(나스닥) 마스터 발견: '{p.name}' 탭 분할 정밀 파싱 시작...")
                try:
                    # 💡 한글이 깨지거나 잘리지 않도록 cp949 인코딩과 깨진 바이트 무시 옵션(errors='ignore') 적용
                    with open(p, "r", encoding="cp949", errors="ignore") as f:
                        for line in f:
                            if not line.strip():
                                continue

                            # 🌟 개발자님이 보내주신 대박 단서! 데이터가 탭('\t')으로 구분되어 있습니다.
                            parts = line.split('\t')

                            # 데이터 열이 충분히 존재하는지 확인 (최소 7개 열 이상)
                            if len(parts) >= 7:
                                ticker = parts[4].strip()  # 5번째 열: 티커 (예: AAPL, AAL)
                                kr_name = parts[6].strip()  # 7번째 열: 한글 종목명 (예: 아메리칸 에어라인스 그룹)
                                en_name = parts[7].strip() if len(parts) > 7 else ""  # 8번째 열: 영문 종목명

                                if ticker and (kr_name or en_name):
                                    # 실거래에 사용되는 이름 유연성 확보를 위해 전부 등록
                                    clean_ticker = ticker.lower()
                                    master_data[clean_ticker] = {"code": ticker, "name": kr_name or en_name}

                                    if kr_name:
                                        master_data[kr_name.lower().replace(" ", "")] = {"code": ticker,
                                                                                         "name": kr_name}
                                    if en_name:
                                        master_data[en_name.lower().replace(" ", "")] = {"code": ticker,
                                                                                         "name": kr_name or en_name}
                except Exception as e:
                    print(f"⚠️ 해외 파일 '{p.name}' 처리 중 오류: {e}")

    print(f"✨ [STOCK_MASTER] >>> 총 {file_count}개의 로우 데이터 파일 병합 완료!")

    # 3️⃣ 3구역: 핵심 필수 우량주 최종 가드라인 (혹시 모를 누락 방지)
    essential_stocks = {
        "삼성전자": "005930", "sk하이닉스": "000660", "삼성sdi": "006400",
        "apple": "AAPL", "애플": "AAPL", "tesla": "TSLA", "테슬라": "TSLA", "nvidia": "NVDA", "엔비디아": "NVDA"
    }
    for name, code in essential_stocks.items():
        clean_name = name.lower().replace(" ", "")
        if clean_name not in master_data:
            master_data[clean_name] = {"code": code, "name": name}

    # 완성된 대형 사전을 로컬에 영구 저장
    try:
        with open(MASTER_FILE, "w", encoding="utf-8") as f:
            json.dump(master_data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

    STOCK_MASTER = master_data
    print(f"✅ [구축 완료] 총 {len(STOCK_MASTER)}개 국내/외 종목 기반 최종 무차단 사전 로드 완료!")


# 서버 가동 시점에 사전 연동 초기화
init_stock_master()


def get_stock_info(keyword):
    """ 100% 오프라인 초고속 매칭 엔진 """
    if not keyword:
        return None, None

    keyword = keyword.strip()
    decoded_keyword = urllib.parse.unquote(keyword)

    if decoded_keyword.isdigit():
        return decoded_keyword, decoded_keyword
    if decoded_keyword.isupper() and len(decoded_keyword) <= 5:
        return decoded_keyword, decoded_keyword

    clean_keyword = decoded_keyword.lower().replace(" ", "")

    # 1. 완벽 일치 검색
    if clean_keyword in STOCK_MASTER:
        return STOCK_MASTER[clean_keyword]['code'], STOCK_MASTER[clean_keyword]['name']

    # 2. 부분 일치 유연 검색
    for clean_name, data in STOCK_MASTER.items():
        if clean_keyword in clean_name or clean_name in clean_keyword:
            print(f"🎯 [로컬 통합 매칭] {decoded_keyword} -> {data['name']}({data['code']})")
            return data['code'], data['name']

    return decoded_keyword, decoded_keyword