"""GitHub Actions 1회 실행 스크립트 — streak 포함 저장"""
import logging
import os
import sys
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

from screener import screen_stocks
from storage import save, get_streak_map


def main() -> int:
    date = datetime.now().strftime("%Y%m%d")
    logger.info(f"=== GitHub Actions 스크리닝: {date} ===")

    results = screen_stocks(date)

    # 1차 저장 (streak 계산을 위해 파일 먼저 생성)
    save(date, results)

    # streak 계산 후 각 종목에 추가
    streak_map = get_streak_map(date)
    for r in results:
        r["streak"] = streak_map.get(r["ticker"], 1)

    # streak 포함 재저장
    save(date, results)

    logger.info(f"=== 완료: {len(results)}개 신호 ===")
    for r in results:
        streak_info = f" [{r['streak']}일 연속]" if r.get("streak", 1) > 1 else ""
        logger.info(
            f"  {r['name']}({r['ticker']}) "
            f"+{r['change_rate']}% | {r['volume_surge']}배↑{streak_info}"
        )

    return len(results)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)
