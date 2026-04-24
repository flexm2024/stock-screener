"""날짜별 스크리닝 결과 저장/로드"""
import json
import os
from typing import Dict, List, Optional

RESULTS_DIR = "results"


def save(date: str, results: List[Dict]):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


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
