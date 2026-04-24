"""
카카오 OAuth 초기 설정 스크립트
최초 1회만 실행하면 됩니다.
"""
import urllib.parse
import sys
from config import KAKAO_REST_API_KEY, KAKAO_REDIRECT_URI, KAKAO_AUTH_URL

if not KAKAO_REST_API_KEY:
    print("[오류] .env 파일에 KAKAO_REST_API_KEY를 먼저 설정하세요.")
    print("  1. .env.example을 .env로 복사")
    print("  2. KAKAO_REST_API_KEY=여기에_키_입력")
    sys.exit(1)

print("=" * 60)
print("카카오 인증 설정")
print("=" * 60)
print()
print("【사전 준비】")
print("  1. https://developers.kakao.com 에서 애플리케이션 생성")
print("  2. 앱 → 카카오 로그인 → 활성화 ON")
print("  3. 앱 → 카카오 로그인 → Redirect URI 추가:")
print(f"     {KAKAO_REDIRECT_URI}")
print("  4. 앱 → 동의항목 → '카카오톡 메시지 전송' 설정")
print()

# 인증 URL 생성
params = urllib.parse.urlencode({
    "response_type": "code",
    "client_id": KAKAO_REST_API_KEY,
    "redirect_uri": KAKAO_REDIRECT_URI,
    "scope": "talk_message",
})
auth_url = f"{KAKAO_AUTH_URL}?{params}"

print("【인증 절차】")
print("  아래 URL을 브라우저에 붙여넣고 카카오 계정으로 로그인하세요:")
print()
print(f"  {auth_url}")
print()
print("  로그인 후 브라우저 주소창에 다음과 같은 URL이 나타납니다:")
print("  https://localhost?code=XXXXXXXX")
print()

redirected_url = input("  리디렉션된 전체 URL을 붙여넣으세요: ").strip()

parsed = urllib.parse.urlparse(redirected_url)
params_qs = urllib.parse.parse_qs(parsed.query)
code = params_qs.get("code", [None])[0]

if not code:
    print("[오류] URL에서 code를 찾을 수 없습니다.")
    sys.exit(1)

print(f"\n인증 코드 확인: {code[:10]}...")
print("토큰 교환 중...")

try:
    from kakao_auth import exchange_code_for_tokens
    tokens = exchange_code_for_tokens(code)
    print()
    print("[성공] 카카오 토큰이 kakao_tokens.json에 저장되었습니다.")
    print("이제 python main.py --now 로 테스트할 수 있습니다.")
except Exception as e:
    print(f"[오류] 토큰 교환 실패: {e}")
    sys.exit(1)
