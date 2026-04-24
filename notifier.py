"""카카오톡 나에게 보내기"""
import json
import logging
import requests
from collections import defaultdict
from typing import Dict, List

from config import KAKAO_SEND_URL, VOLUME_SURGE_RATIO, MIN_PRICE_CHANGE
from kakao_auth import get_valid_access_token

logger = logging.getLogger(__name__)

MAX_TEXT_LEN = 180  # 카카오 텍스트 템플릿 안전 길이


def fmt_val(val: int) -> str:
    """거래대금 억/조 단위 포맷"""
    eok = val / 1_0000_0000
    if eok >= 10000:
        return f"{eok/10000:.1f}조"
    if eok >= 1000:
        return f"{eok/1000:.1f}천억"
    return f"{eok:.0f}억"


def fmt_chg(change_rate: float) -> str:
    arrow = "▲" if change_rate >= 0 else "▼"
    return f"{arrow}{abs(change_rate):.1f}%"


def build_messages(results: List[Dict], date: str) -> List[str]:
    """스크리닝 결과를 카카오 전송용 문자열 리스트로 변환"""
    if not results:
        return [f"[주도섹터신호] {date[:4]}.{date[4:6]}.{date[6:]}\n오늘 신호 종목 없음"]

    # 섹터별 그룹화
    by_sector: Dict[str, List[Dict]] = defaultdict(list)
    for r in results:
        by_sector[r["sector"]].append(r)

    messages = []

    # ── 헤더 ──────────────────────────────────────
    messages.append(
        f"[주도섹터신호] {date[:4]}.{date[4:6]}.{date[6:]}\n"
        f"거래대금 장대양봉 {len(results)}종목 포착\n"
        f"기준: 거래대금 {int(VOLUME_SURGE_RATIO)}배↑ + {MIN_PRICE_CHANGE}%이상"
    )

    # ── 섹터별 블록 ───────────────────────────────
    for sector, sig_stocks in by_sector.items():
        lines = [f"▶ {sector}"]

        # 신호 종목
        for s in sig_stocks:
            lines.append(
                f"🔥 {s['name']}({s['ticker']})\n"
                f"   {fmt_chg(s['change_rate'])} | "
                f"거래대금 {s['volume_surge']}배↑ | "
                f"{fmt_val(s['trading_value'])} | {s['market']}"
            )

        # 섹터 관련주 (첫 신호 종목 기준, 동일 섹터라 동일함)
        related = sig_stocks[0].get("related_stocks", [])
        if related:
            lines.append("[섹터 관련주]")
            for r in related:
                lines.append(
                    f"  {r['name']}({r['ticker']}) "
                    f"{fmt_chg(r['change_rate'])} | {fmt_val(r['trading_value'])}"
                )

        # 블록을 180자 단위로 분할해서 전송
        chunk = "\n".join(lines)
        _split_and_append(messages, chunk)

    messages.append("※ 투자 판단은 본인 책임 / 참고 목적")
    return messages


def _split_and_append(messages: List[str], text: str):
    """180자 초과 시 자연스럽게 분할"""
    while len(text) > MAX_TEXT_LEN:
        split_at = text.rfind("\n", 0, MAX_TEXT_LEN)
        if split_at == -1:
            split_at = MAX_TEXT_LEN
        messages.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text:
        messages.append(text)


def send_text(access_token: str, text: str) -> bool:
    """카카오 텍스트 메시지 1건 전송"""
    template = {
        "object_type": "text",
        "text": text[:200],
        "link": {
            "web_url": "https://finance.naver.com",
            "mobile_web_url": "https://m.finance.naver.com",
        },
    }
    resp = requests.post(
        KAKAO_SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
    )
    if resp.status_code == 200 and resp.json().get("result_code") == 0:
        return True
    logger.error(f"카카오 전송 실패: {resp.status_code} {resp.text}")
    return False


def send_screening_result(results: List[Dict], date: str):
    """스크리닝 결과를 카카오톡으로 전송"""
    try:
        token = get_valid_access_token()
    except RuntimeError as e:
        logger.error(str(e))
        return

    messages = build_messages(results, date)
    success = 0
    for msg in messages:
        if send_text(token, msg):
            success += 1
        else:
            logger.warning(f"메시지 전송 실패: {msg[:40]}...")

    logger.info(f"카카오 전송 완료: {success}/{len(messages)}건")
