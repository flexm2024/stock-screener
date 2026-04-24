"""
주도 섹터 신호 스크리너 - 메인 실행 파일

사용법:
  python main.py          → 매일 15:40 KST 자동 실행 (스케줄러 모드)
  python main.py --now    → 즉시 1회 실행
"""
import sys
import logging
import schedule
import time
from datetime import datetime

from screener import screen_stocks
import storage
from config import SCHEDULE_TIME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("screener.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def run():
    logger.info("===== 스크리닝 시작 =====")
    date = datetime.now().strftime("%Y%m%d")

    # 이미 오늘 실행 결과가 있으면 스킵 (중복 방지)
    if "--force" not in sys.argv and storage.load(date) is not None:
        logger.info(f"오늘({date}) 결과가 이미 있습니다. 건너뜁니다. (강제 실행: --force)")
        return

    results = screen_stocks(date)
    storage.save(date, results)
    logger.info(f"결과 저장 완료: results/{date}.json ({len(results)}개 종목)")

    # 카카오톡 알림 (선택 — 설정된 경우에만)
    try:
        from notifier import send_screening_result
        from kakao_auth import load_tokens
        if load_tokens():
            send_screening_result(results, date)
    except Exception as e:
        logger.warning(f"카카오 알림 생략: {e}")

    logger.info("===== 스크리닝 완료 =====")


if __name__ == "__main__":
    if "--now" in sys.argv or "--force" in sys.argv:
        run()
    else:
        schedule.every().day.at(SCHEDULE_TIME).do(run)
        logger.info(f"스케줄러 시작: 매일 {SCHEDULE_TIME} KST에 자동 실행")
        logger.info("즉시 실행: python main.py --now")
        logger.info("강제 재실행: python main.py --force")
        while True:
            schedule.run_pending()
            time.sleep(30)
