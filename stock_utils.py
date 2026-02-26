import FinanceDataReader as fdr

print("📚 [stock_utils] 한국 주식 이름 사전 로딩 중...")
krx_list = fdr.StockListing('KRX')
print("✅ [stock_utils] 주식 사전 로딩 완료!")


def get_stock_info(keyword):
    """주식 이름이나 코드를 입력받아 (코드, 이름) 두 가지를 모두 반환합니다."""
    keyword = keyword.strip()

    # 1. 입력한 게 숫자(코드)라면? -> 사전에서 이름을 찾음
    if keyword.isdigit():
        result = krx_list[krx_list['Code'] == keyword]
        if not result.empty:
            return keyword, result.iloc[0]['Name']
        return keyword, keyword  # 사전에 없는 코드면 그냥 둘 다 코드로 반환

    # 2. 한글(이름)이라면? -> 사전에서 코드를 찾음
    result = krx_list[krx_list['Name'] == keyword]
    if not result.empty:
        return result.iloc[0]['Code'], keyword

    # 3. 사전에 없는 이상한 값이라면?
    return None, None