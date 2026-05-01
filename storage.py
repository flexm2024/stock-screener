"""날짜별 스크리닝 결과 저장/로드"""
import json
import os
import shutil
from typing import Dict, List, Optional

RESULTS_DIR = "results"
DEPLOY_DIR  = os.path.join("pwa_deploy", "results")


def _write_index():
    """results/index.json 재생성 — PWA 뷰어가 날짜 목록을 읽는 용도"""
    dates = available_dates()
    path = os.path.join(RESULTS_DIR, "index.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dates, f)


def _sync_deploy(date: str):
    """pwa_deploy/results/ 를 최신 상태로 동기화"""
    os.makedirs(DEPLOY_DIR, exist_ok=True)
    shutil.copy(
        os.path.join(RESULTS_DIR, f"{date}.json"),
        os.path.join(DEPLOY_DIR,  f"{date}.json"),
    )
    shutil.copy(
        os.path.join(RESULTS_DIR, "index.json"),
        os.path.join(DEPLOY_DIR,  "index.json"),
    )


def save(date: str, results: List[Dict]):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    _write_index()
    _sync_deploy(date)


def load(date: str) -> Optional[List[Dict]]:
    path = os.path.join(RESULTS_DIR, f"{date}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def available_dates() -> List[str]:
    """저장된 날짜 목록 (최신순)"""
    if not os.path.exists(RESULTS_DIR):
        return []
    dates = [
        f.replace(".json", "")
        for f in os.listdir(RESULTS_DIR)
        if f.endswith(".json") and f[:8].isdigit()
    ]
    return sorted(dates, reverse=True)


def fmt_date_label(date: str) -> str:
    """20260423 → 2026.04.23"""
    return f"{date[:4]}.{date[4:6]}.{date[6:]}"


def get_streak_map(current_date: str) -> dict:
    """
    current_date 기준 각 ticker가 몇 일 연속 신호에 나타났는지 반환.
    예: {"005930": 3, "000660": 1}
    """
    current_results = load(current_date)
    if not current_results:
        return {}

    target_tickers = {r["ticker"] for r in current_results}
    streak: dict = {t: 1 for t in target_tickers}

    past_dates = sorted(
        [d for d in available_dates() if d < current_date],
        reverse=True,
    )

    still_running = set(target_tickers)

    for d in past_dates:
        if not still_running:
            break
        data = load(d)
        appeared = {r["ticker"] for r in data} if data else set()
        newly_stopped = set()
        for t in still_running:
            if t in appeared:
                streak[t] += 1
            else:
                newly_stopped.add(t)
        still_running -= newly_stopped

    return streak
