import os
from dotenv import load_dotenv

load_dotenv()

# 카카오 설정
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_REDIRECT_URI = "https://localhost"
KAKAO_TOKEN_FILE = "kakao_tokens.json"
KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

# 스크리닝 기준 (영상 기반)
MIN_TRADING_VALUE = 200_000_000_000  # 최소 거래대금: 2000억원
VOLUME_SURGE_RATIO = 3.0            # 20일 평균 대비 거래대금 배수 (3배 이상)
MIN_PRICE_CHANGE = 3.0              # 최소 상승률 (%)
MIN_BODY_RATIO = 0.5                # 캔들 몸통 비율 (몸통/전체 50% 이상 = 장대양봉)
MA_PERIOD = 20                      # 거래대금 이동평균 기간 (거래일 기준)
MAX_RESULTS = 20                    # 최대 결과 종목 수

# 스크리닝 대상 시장
MARKETS = ["KOSPI", "KOSDAQ"]

# 매일 실행 시각 (한국시간 기준, 장 마감 후)
SCHEDULE_TIME = "15:40"  # 장 마감(15:30) 10분 후
