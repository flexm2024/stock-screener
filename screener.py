"""
한국 주식 스크리닝: 거래대금 급증 + 장대양봉 포착
- 오늘 데이터: FinanceDataReader (KOSPI/KOSDAQ 전체 한 번에)
- 업종 정보 : KIND (한국거래소 기업공시채널)
- 히스토리  : pykrx 개별 종목 조회 (거래량 × 종가 = 거래대금 근사)
"""
import io
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
import FinanceDataReader as fdr
from pykrx import stock as pykrx

from config import (
    MA_PERIOD, MARKETS, MAX_RESULTS,
    MIN_BODY_RATIO, MIN_PRICE_CHANGE,
    MIN_TRADING_VALUE, VOLUME_SURGE_RATIO,
)

logger = logging.getLogger(__name__)

MAX_RELATED = 5

_KIND_PARAMS_BASE = {
    "method": "download",
    "pageIndex": 1,
    "currentPageSize": 5000,
    "searchType": 13,
}
_KIND_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "http://kind.krx.co.kr/",
}
_KIND_MARKET_MAP = {"KOSPI": "stockMkt", "KOSDAQ": "kosdaqMkt"}


# ── 업종/이름 매핑 ─────────────────────────────────────────
def get_sector_and_name_map() -> Tuple[Dict[str, str], Dict[str, str]]:
    """KIND에서 종목코드 → 업종명, 종목코드 → 회사명 매핑"""
    sector_map: Dict[str, str] = {}
    name_map: Dict[str, str] = {}

    for market, market_type in _KIND_MARKET_MAP.items():
        try:
            params = {**_KIND_PARAMS_BASE, "marketType": market_type}
            r = requests.get(
                "http://kind.krx.co.kr/corpgeneral/corpList.do",
                params=params, headers=_KIND_HEADERS, timeout=15,
            )
            r.encoding = "euc-kr"
            df = pd.read_html(io.StringIO(r.text))[0]
            df.columns = [
                "회사명", "업종구분", "단축코드", "업종명",
                "주요제품", "상장일", "결산월", "대표자", "홈페이지", "지역",
            ]
            # 6자리 숫자 코드만 사용 (펀드/스팩 코드 제외)
            df["단축코드"] = df["단축코드"].astype(str).str.zfill(6)
            df = df[df["단축코드"].str.match(r"^\d{6}$")]

            for _, row in df.iterrows():
                t = row["단축코드"]
                sector_map[t] = str(row["업종명"])
                name_map[t] = str(row["회사명"])

            logger.info(f"KIND 로드: {market} {len(df)}개 종목")
        except Exception as e:
            logger.warning(f"KIND 조회 실패 ({market}): {e}")

    return sector_map, name_map


# ── 오늘 시장 데이터 ──────────────────────────────────────
def get_today_market() -> pd.DataFrame:
    """FinanceDataReader로 KOSPI + KOSDAQ 오늘 전체 데이터"""
    frames = []
    for market in MARKETS:
        try:
            df = fdr.StockListing(market)
            df["Market"] = market
            frames.append(df)
            logger.info(f"FDR 로드: {market} {len(df)}개")
        except Exception as e:
            logger.error(f"FDR 로드 실패 ({market}): {e}")

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined["Code"] = combined["Code"].astype(str).str.zfill(6)
    for col in ["Open", "High", "Low", "Close", "Amount", "ChagesRatio"]:
        combined[col] = pd.to_numeric(combined.get(col, 0), errors="coerce").fillna(0)
    return combined


# ── 1차 필터 ─────────────────────────────────────────────
def prefilter(df: pd.DataFrame) -> pd.DataFrame:
    """양봉 + 최소 거래대금 + 최소 상승률 + 장대양봉"""
    f = df[(df["Close"] > df["Open"]) & (df["Open"] > 0)].copy()
    f = f[f["Amount"] >= MIN_TRADING_VALUE]
    f = f[f["ChagesRatio"] >= MIN_PRICE_CHANGE]

    body = f["Close"] - f["Open"]
    rng  = (f["High"] - f["Low"]).replace(0, pd.NA)
    f["body_ratio"] = (body / rng).fillna(1.0)
    f = f[f["body_ratio"] >= MIN_BODY_RATIO]

    return f


# ── 히스토리 거래대금 MA ──────────────────────────────────
def get_hist_amount_ma(ticker: str, before_date: str, period: int) -> float:
    """
    pykrx 개별 종목 조회로 과거 N거래일 평균 거래대금 계산.
    거래대금 = 거래량 × 종가 근사값 사용.
    """
    try:
        end_dt   = datetime.strptime(before_date, "%Y%m%d") - timedelta(days=1)
        start_dt = end_dt - timedelta(days=period * 3)
        df = pykrx.get_market_ohlcv_by_date(
            start_dt.strftime("%Y%m%d"),
            end_dt.strftime("%Y%m%d"),
            ticker,
        )
        if df.empty or len(df) < 3:
            return 0.0

        # 컬럼 이름이 인코딩 문제로 깨질 수 있어 위치 기반 사용
        # 순서: 시가(0) 고가(1) 저가(2) 종가(3) 거래량(4) 등락률(5)
        close_col  = df.columns[3]
        volume_col = df.columns[4]

        amount_series = df[volume_col] * df[close_col]
        return float(amount_series.tail(period).mean())
    except Exception:
        return 0.0


# ── 관련주 부착 ────────────────────────────────────────────
def attach_related(
    results: List[Dict],
    sector_map: Dict[str, str],
    name_map: Dict[str, str],
    today_indexed: pd.DataFrame,
):
    """각 신호 종목에 동일 업종 관련주 추가 (신호 종목 제외, 거래대금 순)"""
    sector_to_tickers: Dict[str, List[str]] = defaultdict(list)
    for ticker, sector in sector_map.items():
        sector_to_tickers[sector].append(ticker)

    signal_set = {r["ticker"] for r in results}

    for result in results:
        sector = result.get("sector", "기타")
        if sector == "기타":
            result["related_stocks"] = []
            continue

        related = []
        for t in sector_to_tickers.get(sector, []):
            if t in signal_set or t not in today_indexed.index:
                continue
            row = today_indexed.loc[t]
            tval = float(row.get("Amount", 0))
            if tval <= 0:
                continue
            related.append({
                "ticker": t,
                "name": name_map.get(t, t),
                "close": int(float(row.get("Close", 0))),
                "change_rate": round(float(row.get("ChagesRatio", 0)), 2),
                "trading_value": int(tval),
            })

        related.sort(key=lambda x: x["trading_value"], reverse=True)
        result["related_stocks"] = related[:MAX_RELATED]


# ── 메인 스크리닝 ─────────────────────────────────────────
def screen_stocks(date: Optional[str] = None) -> List[Dict]:
    """
    전체 스크리닝 실행.
    반환: 신호 종목 리스트 (섹터·관련주 포함, 거래대금 배수 내림차순)
    """
    if date is None:
        date = datetime.now().strftime("%Y%m%d")

    logger.info(f"=== 스크리닝 시작: {date} ===")

    # 1. 업종·이름 맵
    sector_map, name_map = get_sector_and_name_map()

    # 2. 오늘 전체 시장 데이터
    today_df = get_today_market()
    if today_df.empty:
        logger.error("오늘 시장 데이터 없음")
        return []

    # 3. 1차 필터
    filtered = prefilter(today_df)
    logger.info(f"1차 필터 통과: {len(filtered)}종목 → 거래대금 배수 계산 시작")

    # 4. 거래대금 배수 필터 (개별 히스토리)
    results: List[Dict] = []
    for _, row in filtered.iterrows():
        ticker      = str(row["Code"])
        today_amount = float(row["Amount"])

        time.sleep(0.2)
        ma = get_hist_amount_ma(ticker, date, MA_PERIOD)
        if ma <= 0:
            continue
        surge = today_amount / ma
        if surge < VOLUME_SURGE_RATIO:
            continue

        name = name_map.get(ticker, str(row.get("Name", ticker)))
        results.append({
            "ticker":        ticker,
            "name":          name,
            "market":        str(row["Market"]),
            "close":         int(row["Close"]),
            "change_rate":   round(float(row["ChagesRatio"]), 2),
            "trading_value": int(today_amount),
            "volume_surge":  round(surge, 1),
            "body_ratio":    round(float(row["body_ratio"]), 2),
            "sector":        sector_map.get(ticker, "기타"),
        })
        logger.info(
            f"신호: {name}({ticker}) "
            f"+{row['ChagesRatio']:.1f}% | {surge:.1f}배↑"
        )

    # 5. 관련주 부착
    if results:
        today_indexed = today_df.set_index("Code")
        today_indexed = today_indexed[~today_indexed.index.duplicated(keep="first")]
        attach_related(results, sector_map, name_map, today_indexed)

    results.sort(key=lambda x: x["volume_surge"], reverse=True)
    logger.info(f"=== 스크리닝 완료: 총 {len(results)}개 신호 ===")
    return results[:MAX_RESULTS]
