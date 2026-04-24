"""주도 섹터 신호 스크리너 - 웹 대시보드"""
import streamlit as st
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import pandas as pd

import storage
from screener import screen_stocks

# ── 한국 시간 ─────────────────────────────────────────────
KST = timezone(timedelta(hours=9))

def now_kst() -> datetime:
    return datetime.now(KST)

def today_str() -> str:
    return now_kst().strftime("%Y%m%d")

def today_label() -> str:
    dt = now_kst()
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return dt.strftime(f"%Y년 %m월 %d일 ({weekdays[dt.weekday()]})")

def is_after_market_close() -> bool:
    """15:30 이후이면 당일 스크리닝 가능"""
    t = now_kst()
    return t.hour > 15 or (t.hour == 15 and t.minute >= 30)


# ── 페이지 설정 ────────────────────────────────────────────
st.set_page_config(
    page_title="주도 섹터 신호 스크리너",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');

/* ── 디자인 토큰 ──────────────────────────────────── */
:root {
  --c-bg:          #f4f7ff;
  --c-surface:     #ffffff;
  --c-border:      rgba(40, 96, 255, 0.13);
  --c-text:        #0b1120;
  --c-muted:       #4a5680;
  --c-accent:      #2860ff;
  --c-accent-dark: #1a4fe0;
  --c-accent-light:#5585ff;
  --c-mint:        #20cc80;
  --c-danger:      #ff4060;
  --c-warning:     #f0a020;
  --c-grid:        rgba(40, 96, 255, 0.05);
  --c-shadow:      rgba(40, 96, 255, 0.08);
}

/* ── 애니메이션 ───────────────────────────────────── */
@keyframes shimmer {
  0%   { background-position: -200% center; }
  100% { background-position:  200% center; }
}
@keyframes fadeInUp {
  0%   { opacity: 0; transform: translateY(28px); }
  100% { opacity: 1; transform: translateY(0);    }
}
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(40,96,255,0.35); }
  50%       { box-shadow: 0 0 0 8px rgba(40,96,255,0);  }
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0; }
}

/* ── Streamlit 기본 헤더 숨기기 ───────────────────── */
header[data-testid="stHeader"] { display: none !important; }
#stDecoration                   { display: none !important; }
.stMainBlockContainer           { padding-top: 72px !important; }

/* ── 커스텀 상단 Navbar ────────────────────────────── */
.fm-navbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 9999;
  height: 52px;
  background: rgba(244, 247, 255, 0.88);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(40, 96, 255, 0.13);
  display: flex;
  align-items: center;
  padding: 0 28px;
  gap: 0;
}
.fm-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 800;
  font-size: 0.95rem;
  color: var(--c-text);
  letter-spacing: -0.03em;
  white-space: nowrap;
}
.fm-logo-dot {
  width: 9px; height: 9px;
  background: linear-gradient(135deg, #2860ff, #20cc80);
  border-radius: 50%;
  flex-shrink: 0;
  animation: pulse-glow 2.4s ease-in-out infinite;
}
.fm-nav-sep {
  margin: 0 14px;
  color: rgba(40,96,255,0.25);
  font-weight: 300;
  font-size: 1.1rem;
}
.fm-nav-sub {
  font-size: 0.8rem;
  color: var(--c-muted);
  font-weight: 500;
  letter-spacing: 0.01em;
}

/* ── Hero 타이틀 섹션 ─────────────────────────────── */
.fm-hero {
  text-align: center;
  padding: 44px 20px 28px;
  animation: 0.55s cubic-bezier(.22,1,.36,1) both fadeInUp;
}
.fm-hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(40, 96, 255, 0.08);
  border: 1px solid rgba(40, 96, 255, 0.25);
  border-radius: 999px;
  padding: 5px 16px;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--c-accent);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 22px;
}
.fm-hero-badge-dot {
  width: 5px; height: 5px;
  background: var(--c-mint);
  border-radius: 50%;
  display: inline-block;
}
.fm-hero-title {
  font-size: clamp(2.2rem, 5.5vw, 3.8rem);
  font-weight: 900;
  line-height: 1.05;
  letter-spacing: -0.04em;
  color: var(--c-text);
  margin: 0 0 6px;
}
.fm-shimmer {
  background: linear-gradient(
    90deg,
    var(--c-text)   0%,
    var(--c-accent) 28%,
    var(--c-mint)   55%,
    var(--c-accent) 72%,
    var(--c-text)  100%
  );
  background-size: 250% auto;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: shimmer 4s linear infinite;
  display: inline;
}
.fm-hero-cursor {
  display: inline-block;
  width: 3px; height: 0.85em;
  background: var(--c-accent);
  border-radius: 2px;
  vertical-align: middle;
  margin-left: 4px;
  animation: blink 0.9s step-end infinite;
}
.fm-hero-sub {
  font-size: 0.92rem;
  color: var(--c-muted);
  font-weight: 400;
  margin: 12px 0 0;
  letter-spacing: -0.01em;
}
.fm-accent-bar {
  width: 3rem;
  height: 3px;
  background: linear-gradient(90deg, var(--c-accent), var(--c-mint));
  border-radius: 999px;
  margin: 18px auto 0;
}

/* ── 전역 폰트 & 배경 ─────────────────────────────── */
html, body, [class*="css"] {
  font-family: "Pretendard Variable", Pretendard, -apple-system, sans-serif !important;
}
[data-testid="stAppViewContainer"] {
  background: var(--c-bg) !important;
}
[data-testid="stAppViewContainer"] > .main {
  background: transparent !important;
}

/* ── 그리드 오버레이 ──────────────────────────────── */
[data-testid="stAppViewContainer"]::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-image:
    linear-gradient(var(--c-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--c-grid) 1px, transparent 1px);
  background-size: 48px 48px;
}

/* ── 사이드바 ─────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.88) !important;
  backdrop-filter: blur(16px) !important;
  border-right: 1px solid var(--c-border) !important;
}
[data-testid="stSidebar"] * { color: var(--c-text) !important; }
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stSlider p { color: var(--c-muted) !important; }

/* ── 메인 영역 텍스트 ─────────────────────────────── */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span { color: var(--c-text); }

/* ── 탭 ───────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: rgba(255,255,255,0.7) !important;
  border: 1px solid var(--c-border) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  backdrop-filter: blur(12px);
  gap: 2px;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: 8px !important;
  color: var(--c-muted) !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
  padding: 6px 16px !important;
  transition: all 0.2s !important;
}
.stTabs [aria-selected="true"] {
  background: var(--c-accent) !important;
  color: #fff !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 12px var(--c-shadow) !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"]    { display: none !important; }

/* ── 버튼 ─────────────────────────────────────────── */
.stButton button[kind="primary"] {
  background: linear-gradient(135deg, var(--c-accent), var(--c-accent-dark)) !important;
  border: none !important;
  border-radius: 10px !important;
  color: #fff !important;
  font-weight: 700 !important;
  font-size: 0.87rem !important;
  letter-spacing: 0.01em !important;
  box-shadow: 0 4px 18px var(--c-shadow) !important;
  transition: all 0.2s !important;
}
.stButton button[kind="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 28px rgba(40,96,255,0.28) !important;
}
.stButton button[kind="secondary"] {
  background: rgba(40,96,255,0.06) !important;
  border: 1px solid rgba(40,96,255,0.3) !important;
  border-radius: 10px !important;
  color: var(--c-accent) !important;
  font-weight: 600 !important;
  transition: all 0.2s !important;
}
.stButton button[kind="secondary"]:hover {
  background: rgba(40,96,255,0.12) !important;
  transform: translateY(-2px) !important;
}

/* ── 메트릭 카드 ──────────────────────────────────── */
[data-testid="stMetric"] {
  background: rgba(255,255,255,0.85) !important;
  border: 1px solid var(--c-border) !important;
  border-radius: 16px !important;
  padding: 18px 22px !important;
  backdrop-filter: blur(12px) !important;
  box-shadow: 0 4px 20px var(--c-shadow) !important;
  transition: transform 0.25s, box-shadow 0.25s !important;
}
[data-testid="stMetric"]:hover {
  transform: translateY(-3px) !important;
  box-shadow: 0 12px 36px var(--c-shadow) !important;
}
[data-testid="stMetricLabel"] { color: var(--c-muted) !important; font-size: 0.82rem !important; font-weight: 600 !important; }
[data-testid="stMetricValue"] { color: var(--c-accent) !important; font-weight: 800 !important; }
[data-testid="stMetricDelta"] { color: var(--c-mint) !important; }

/* ── 구분선 ───────────────────────────────────────── */
hr { border-color: var(--c-border) !important; }

/* ── 신호 카드 ────────────────────────────────────── */
.sig-card {
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px);
  border: 1px solid var(--c-border);
  border-left: 4px solid var(--c-accent);
  border-radius: 16px;
  padding: 16px 20px;
  margin-bottom: 10px;
  transition: transform 0.25s, box-shadow 0.25s, border-color 0.25s;
  box-shadow: 0 4px 20px var(--c-shadow);
}
.sig-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 40px rgba(40,96,255,0.12);
  border-color: rgba(40,96,255,0.35);
}

.sig-name {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--c-text);
  letter-spacing: -0.025em;
}
.sig-meta  { font-size: 0.84rem; color: var(--c-muted); margin-top: 6px; }

.up   { color: var(--c-danger);  font-weight: 600; }
.down { color: var(--c-accent);  font-weight: 600; }

.tag {
  background: rgba(40,96,255,0.06);
  border: 1px solid rgba(40,96,255,0.15);
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 0.75rem;
  color: var(--c-muted);
  margin-right: 4px;
  font-family: "JetBrains Mono", monospace;
}

/* ── 섹터 제목 ────────────────────────────────────── */
.sector-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 20px 0 12px;
}
.sector-dot {
  width: 8px; height: 8px;
  background: linear-gradient(135deg, var(--c-accent), var(--c-mint));
  border-radius: 50%;
  flex-shrink: 0;
}
.sector-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--c-accent);
  letter-spacing: -0.025em;
  margin: 0;
}
.sector-bar {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(40,96,255,0.3), transparent);
}

/* ── 날짜 헤더 ────────────────────────────────────── */
.date-big  { font-size: 1.55rem; font-weight: 800; color: var(--c-text); letter-spacing: -0.03em; }
.date-sub  { font-size: 0.88rem; color: var(--c-muted); margin-top: 2px; }

/* ── 빈 상태 ──────────────────────────────────────── */
.no-signal {
  text-align: center;
  padding: 60px 40px;
  color: var(--c-muted);
  font-size: 0.95rem;
  background: rgba(255,255,255,0.7);
  border: 1px solid var(--c-border);
  border-radius: 20px;
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 20px var(--c-shadow);
}

/* ── 스피너 / info 박스 ───────────────────────────── */
[data-testid="stAlert"] {
  background: rgba(40,96,255,0.06) !important;
  border: 1px solid rgba(40,96,255,0.2) !important;
  border-radius: 12px !important;
  color: var(--c-accent) !important;
}

/* ── 데이터프레임 ─────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--c-border) !important;
  border-radius: 12px !important;
  overflow: hidden;
}
</style>
""", unsafe_allow_html=True)


# ── 유틸 ─────────────────────────────────────────────────
def fmt_val(val: int) -> str:
    eok = val / 1e8
    if eok >= 10000: return f"{eok/10000:.1f}조"
    if eok >= 1000:  return f"{eok/1000:.1f}천억"
    return f"{eok:.0f}억"

def chg_html(chg: float) -> str:
    cls = "up" if chg >= 0 else "down"
    arrow = "▲" if chg >= 0 else "▼"
    return f'<span class="{cls}">{arrow}{abs(chg):.1f}%</span>'

def render_signal_card(s: dict):
    st.markdown(f"""
    <div class="sig-card">
      <div class="sig-name">{s['name']}
        <span style="font-size:0.82rem;color:var(--c-muted);margin-left:8px;font-weight:500;font-family:'JetBrains Mono',monospace">{s['ticker']}</span>
      </div>
      <div class="sig-meta">
        {chg_html(s['change_rate'])} &nbsp;
        <span class="tag">거래대금 {s['volume_surge']}배↑</span>
        <span class="tag">{fmt_val(s['trading_value'])}</span>
        <span class="tag">{s['market']}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_related(related: list):
    if not related:
        return
    st.caption("섹터 관련주 (거래대금 순)")
    df = pd.DataFrame(related)[["name", "ticker", "change_rate", "trading_value"]]
    df.columns = ["종목명", "코드", "등락률", "거래대금"]
    df["거래대금"] = df["거래대금"].apply(fmt_val)
    df["등락률"]  = df["등락률"].apply(lambda x: f"{'▲' if x>=0 else '▼'}{abs(x):.1f}%")
    st.dataframe(df, hide_index=True, use_container_width=True)

def run_and_save(date: str) -> list:
    results = screen_stocks(date)
    storage.save(date, results)
    return results

def render_results(results: list, date: str):
    """결과 화면 렌더링"""
    if not results:
        st.markdown('<div class="no-signal"><span style="font-size:2rem;display:block;margin-bottom:12px">📭</span>오늘 신호 종목 없음<br><span style="font-size:0.82rem;color:var(--c-muted)">기준에 맞는 장대양봉+거래대금 급증 종목이 없습니다</span></div>', unsafe_allow_html=True)
        return

    total_sectors = len({r["sector"] for r in results})
    top_stock = max(results, key=lambda x: x["volume_surge"])

    m1, m2, m3 = st.columns(3)
    m1.metric("신호 종목", f"{len(results)}개")
    m2.metric("활성 섹터", f"{total_sectors}개")
    m3.metric("최고 거래대금 배수", f"{top_stock['volume_surge']}배↑", top_stock["name"])

    st.divider()

    by_sector = defaultdict(list)
    for r in results:
        by_sector[r["sector"]].append(r)

    sectors = list(by_sector.items())
    for i in range(0, len(sectors), 2):
        cols = st.columns(2)
        for ci, (sector, stocks) in enumerate(sectors[i:i+2]):
            with cols[ci]:
                st.markdown(f'''
                <div class="sector-header">
                  <div class="sector-dot"></div>
                  <div class="sector-title">{sector}</div>
                  <div class="sector-bar"></div>
                </div>''', unsafe_allow_html=True)
                for s in stocks:
                    render_signal_card(s)
                render_related(stocks[0].get("related_stocks", []))


# ── 사이드바 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-size:1.1rem;font-weight:800;color:var(--c-text);letter-spacing:-0.025em;margin-bottom:4px">스크리닝 설정</div><div style="width:2rem;height:3px;background:linear-gradient(90deg,#2860ff,#20cc80);border-radius:999px;margin-bottom:20px"></div>', unsafe_allow_html=True)
    custom_surge   = st.slider("거래대금 배수 기준", 2.0, 10.0, 3.0, 0.5)
    custom_chg     = st.slider("최소 상승률 (%)", 1.0, 10.0, 3.0, 0.5)
    custom_related = st.slider("관련주 표시 수", 3, 10, 5)

    st.divider()
    st.markdown('<div style="font-size:0.82rem;font-weight:700;color:var(--c-muted);letter-spacing:0.05em;text-transform:uppercase;margin-bottom:8px">날짜별 기록</div>', unsafe_allow_html=True)
    dates = storage.available_dates()
    if dates:
        for d in dates:
            data = storage.load(d)
            cnt = len(data) if data else 0
            label = f"{storage.fmt_date_label(d)}  —  {cnt}종목"
            if st.button(label, key=f"btn_{d}", use_container_width=True):
                st.session_state["selected_date"] = d
    else:
        st.caption("아직 저장된 기록이 없습니다")


# ── 상단 Navbar ───────────────────────────────────────────
st.markdown("""
<div class="fm-navbar">
  <div class="fm-logo">
    <div class="fm-logo-dot"></div>
    스탁
  </div>
  <span class="fm-nav-sep">/</span>
  <span class="fm-nav-sub">주도 섹터 신호 스크리너</span>
</div>
""", unsafe_allow_html=True)

# ── Hero 타이틀 ────────────────────────────────────────────
st.markdown(f"""
<div class="fm-hero">
  <div class="fm-hero-badge">
    <span class="fm-hero-badge-dot"></span>
    KOSPI · KOSDAQ 실시간 신호
  </div>
  <div class="fm-hero-title">
    주도 섹터<br><span class="fm-shimmer">신호 스크리너</span><span class="fm-hero-cursor"></span>
  </div>
  <div class="fm-hero-sub">장대양봉 + 거래대금 급증 종목 자동 포착 &nbsp;·&nbsp; {today_label()}</div>
  <div class="fm-accent-bar"></div>
</div>
""", unsafe_allow_html=True)

# ── 실행 버튼 행 ───────────────────────────────────────────
_, col_btn, _ = st.columns([4, 3, 4])
with col_btn:
    run_today   = st.button("오늘 스크리닝 실행", type="primary", use_container_width=True)
    rerun_today = st.button("재실행 (오늘)", use_container_width=True)

st.divider()


# ── 선택 날짜 결정 ────────────────────────────────────────
selected = st.session_state.get("selected_date", today_str())

# 오늘 버튼 클릭 시
if run_today or rerun_today:
    st.session_state["selected_date"] = today_str()
    selected = today_str()

    import config, screener as _sc
    config.VOLUME_SURGE_RATIO = custom_surge
    config.MIN_PRICE_CHANGE   = custom_chg
    _sc.MAX_RELATED           = custom_related

    with st.spinner(f"KOSPI + KOSDAQ 스크리닝 중... ({today_label()}) — 약 1~3분 소요"):
        results = run_and_save(selected)
    st.session_state["results_cache"] = {selected: results}
    st.rerun()

# 캐시 또는 파일에서 로드
cache = st.session_state.get("results_cache", {})
if selected not in cache:
    loaded = storage.load(selected)
    if loaded is not None:
        cache[selected] = loaded
        st.session_state["results_cache"] = cache

results = cache.get(selected)

# 오늘 데이터 없을 때 자동 실행 (장 마감 후)
if results is None and selected == today_str():
    if is_after_market_close():
        st.info(f"오늘({today_label()}) 스크리닝 결과가 없습니다. 자동으로 실행합니다...")

        import config, screener as _sc
        config.VOLUME_SURGE_RATIO = custom_surge
        config.MIN_PRICE_CHANGE   = custom_chg
        _sc.MAX_RELATED           = custom_related

        with st.spinner("KOSPI + KOSDAQ 스크리닝 중... 약 1~3분 소요"):
            results = run_and_save(today_str())
        cache[today_str()] = results
        st.session_state["results_cache"] = cache
        st.rerun()
    else:
        t = now_kst()
        remain_h = 15 - t.hour
        remain_m = 30 - t.minute if t.hour == 15 else 30
        st.info(f"오늘 장 마감(15:30) 후 자동 스크리닝이 시작됩니다. (현재 {t.strftime('%H:%M')} KST)")
        st.stop()


# ── 날짜 탭 표시줄 ────────────────────────────────────────
all_dates = sorted({today_str()} | set(storage.available_dates()), reverse=True)[:7]

tab_labels = []
for d in all_dates:
    label = "오늘" if d == today_str() else storage.fmt_date_label(d)
    tab_labels.append(label)

tabs = st.tabs(tab_labels)

for i, (tab, d) in enumerate(zip(tabs, all_dates)):
    with tab:
        if d == selected or i == 0:
            if results is None and d == selected:
                st.info("스크리닝 결과가 없습니다. **오늘 스크리닝 실행** 버튼을 눌러주세요.")
            elif d != selected:
                data = storage.load(d)
                if data is not None:
                    st.caption(f"📅 {storage.fmt_date_label(d)} 결과")
                    render_results(data, d)
                else:
                    st.caption(f"{storage.fmt_date_label(d)} 데이터 없음")
            else:
                st.caption(f"📅 {storage.fmt_date_label(selected)} 결과")
                render_results(results, selected)
        else:
            if st.button(f"{storage.fmt_date_label(d)} 결과 보기", key=f"tab_load_{d}"):
                st.session_state["selected_date"] = d
                st.rerun()

st.divider()
st.caption("※ 이 화면의 정보는 참고용이며 투자 판단은 본인 책임입니다.")
