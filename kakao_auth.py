"""카카오 OAuth 토큰 관리"""
import json
import os
import requests
import logging
from datetime import datetime, timedelta
from config import (
    KAKAO_REST_API_KEY, KAKAO_REDIRECT_URI,
    KAKAO_TOKEN_FILE, KAKAO_TOKEN_URL
)

logger = logging.getLogger(__name__)


def load_tokens() -> dict:
    if not os.path.exists(KAKAO_TOKEN_FILE):
        return {}
    with open(KAKAO_TOKEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tokens(tokens: dict):
    with open(KAKAO_TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)
    logger.info("토큰 저장 완료")


def refresh_access_token(refresh_token: str) -> dict:
    """리프레시 토큰으로 액세스 토큰 갱신"""
    resp = requests.post(KAKAO_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": refresh_token,
    })
    resp.raise_for_status()
    return resp.json()


def get_valid_access_token() -> str:
    """유효한 액세스 토큰 반환 (만료 시 자동 갱신)"""
    tokens = load_tokens()
    if not tokens:
        raise RuntimeError("카카오 토큰이 없습니다. setup_kakao.py를 먼저 실행하세요.")

    # 만료 10분 전이면 갱신
    expires_at = tokens.get("expires_at", 0)
    if datetime.now().timestamp() < expires_at - 600:
        return tokens["access_token"]

    logger.info("액세스 토큰 만료됨 → 갱신 중...")
    new_tokens = refresh_access_token(tokens["refresh_token"])

    tokens["access_token"] = new_tokens["access_token"]
    tokens["expires_at"] = datetime.now().timestamp() + new_tokens.get("expires_in", 21600)

    # 리프레시 토큰도 갱신됐으면 저장
    if "refresh_token" in new_tokens:
        tokens["refresh_token"] = new_tokens["refresh_token"]
        tokens["refresh_token_expires_at"] = (
            datetime.now().timestamp() + new_tokens.get("refresh_token_expires_in", 5184000)
        )

    save_tokens(tokens)
    return tokens["access_token"]


def exchange_code_for_tokens(auth_code: str) -> dict:
    """인증 코드로 토큰 교환"""
    resp = requests.post(KAKAO_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": auth_code,
    })
    resp.raise_for_status()
    data = resp.json()

    tokens = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": datetime.now().timestamp() + data.get("expires_in", 21600),
        "refresh_token_expires_at": datetime.now().timestamp() + data.get("refresh_token_expires_in", 5184000),
    }
    save_tokens(tokens)
    return tokens
