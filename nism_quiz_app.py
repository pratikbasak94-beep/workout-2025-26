"""
NISM Series V-A — Mock Quiz App
Requirements: pip install streamlit google-generativeai
Run: streamlit run nism_quiz_app.py
"""

import streamlit as st
import sqlite3
import json
import os
from datetime import datetime

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DB_PATH = "nism_quiz_results.db"
QUESTIONS_PER_SESSION = 5

CHAPTERS = [
    {"id": 1,  "title": "Investment Landscape",                     "emoji": "🌐",
     "topics": "financial goals, savings vs investment, asset classes (equity/debt/real estate/commodities/gold), investment risks (market/credit/liquidity/inflation/interest rate), risk measures (standard deviation, beta, VaR), behavioural biases (anchoring, recency, herding, confirmation, mental accounting, overconfidence, loss aversion, endowment effect), risk profiling, asset allocation strategies, do-it-yourself vs professional help"},
    {"id": 2,  "title": "Concept & Role of a Mutual Fund",          "emoji": "🏦",
     "topics": "mutual fund definition and concept, pooling of funds, NAV, diversification, professional management, types by structure (open-ended, close-ended, interval), by asset class (equity, debt, hybrid, solution-oriented), sub-categories of equity (large cap, mid cap, small cap, multi cap, flexi cap, ELSS, sectoral, thematic, index, ETF), debt categories (liquid, overnight, ultra short, short/medium/long duration, dynamic bond, gilt, credit risk, corporate bond), hybrid categories (conservative, balanced, aggressive, dynamic asset allocation, multi-asset, arbitrage), growth of MF industry in India, AUM trends, SIP"},
    {"id": 3,  "title": "Legal Structure of Mutual Funds",          "emoji": "⚖️",
     "topics": "three-tier structure (sponsor, trust/trustees, AMC), role of sponsor, trust deed, role of trustees, obligations of trustees, AMC registration, role of AMC, restrictions on AMC, service providers: RTA, custodian, depository, auditors, fund accountants, role and function of AMFI, AMFI code of conduct, AMFI Registration Number (ARN), organization structure of AMC"},
    {"id": 4,  "title": "Legal & Regulatory Framework",             "emoji": "📋",
     "topics": "SEBI Act 1992, SEBI (Mutual Funds) Regulations 1996, SEBI regulatory role, AMFI, RBI role for liquid funds, stock exchange listing of close-ended funds, SEBI circulars and guidelines, scheme categorization and rationalization, investor grievance redressal mechanism, SCORES platform, SEBI Ombudsman, due diligence by AMCs for distributors, AMFI code of conduct for intermediaries, risk-o-meter, side pocketing rules, swing pricing, segregated portfolio"},
    {"id": 5,  "title": "Scheme Related Information",               "emoji": "📄",
     "topics": "Scheme Information Document (SID), Statement of Additional Information (SAI), Key Information Memorandum (KIM), addendum, contents of SID, investment objective, asset allocation pattern, investment strategies, risk factors, benchmark, fund manager details, expense ratio disclosure, load structure, SID filing with SEBI, product labelling, risk-o-meter, potential risk class matrix for debt funds"},
    {"id": 6,  "title": "Fund Distribution & Channel Management",   "emoji": "📊",
     "topics": "role of mutual fund distributor, individual vs institutional distributors, banks as distributors, online platforms, MFD vs RIA, direct plan vs regular plan, ARN registration, EUIN, AMFI certification, trail commission vs upfront commission, TER limits, commission disclosure by SEBI, due diligence by AMC, distributor empanelment, change of distributor, nomination facility for distributors, difference between distributor and investment adviser, execution-only platform (EOP)"},
    {"id": 7,  "title": "NAV, TER & Pricing of Units",              "emoji": "🔢",
     "topics": "fair valuation principles, mark-to-market valuation, amortization of debt securities, valuation of non-traded securities, NAV calculation formula (assets minus liabilities divided by units), accrual of income and expenses, NAV computation frequency, declaration of NAV, Total Expense Ratio (TER) components, TER limits for equity and debt schemes, daily TER disclosure, entry load (abolished), exit load, impact of exit load on NAV, accounting standards for mutual funds, annual report and financial statements, segregated portfolio NAV and TER"},
    {"id": 8,  "title": "Taxation",                                 "emoji": "💰",
     "topics": "capital gains taxation for equity funds (LTCG above Rs 1.25 lakh at 12.5%, STCG at 20%), capital gains for debt funds (taxed as per income slab after April 2023), IDCW taxed as income, DDT abolished, stamp duty on purchase at 0.005%, setting off capital gains and losses, STT on equity fund redemptions, ELSS tax benefit under Section 80C up to Rs 1.5 lakh, TDS on capital gains for NRI investors, GST on AMC fees, indexation benefit removed for debt funds after 2023 Finance Act"},
    {"id": 9,  "title": "Investor Services",                        "emoji": "🧾",
     "topics": "NFO process, NFO price Rs 10, ongoing NAV-based pricing, SIP (Systematic Investment Plan), SWP (Systematic Withdrawal Plan), STP (Systematic Transfer Plan), growth option vs IDCW option, dividend payout vs dividend reinvestment, folio number, account statement (CAS), KYC process (CKYC, in-person verification), PAN requirement, minor investors, NRI investors, joint holding, nomination, filling application form, redemption process, cut-off times (liquid fund 1:30 PM, other funds 3 PM), time stamping, turnaround times (T+3 for redemption), SIP registration, SIP auto-debit, switch transaction, transmission of units"},
    {"id": 10, "title": "Risk, Return & Performance of Funds",      "emoji": "📈",
     "topics": "types of risk (systematic vs unsystematic, market/credit/liquidity/interest rate/concentration/reinvestment risk), modified duration and interest rate risk, credit rating and credit risk, portfolio diversification, drivers of return in equity and debt funds, measures of return (absolute return, annualised return, CAGR, XIRR, rolling returns, trailing returns), SEBI norms on return representation, standard deviation, beta, Sharpe ratio, Sortino ratio, Treynor ratio, alpha, R-squared, maximum drawdown, credit risk provisions, side pocketing"},
    {"id": 11, "title": "Mutual Fund Scheme Performance",           "emoji": "🎯",
     "topics": "benchmarks and their importance, Price Return Index (PRI) vs Total Return Index (TRI), SEBI mandate for TRI benchmarks, choosing appropriate benchmark, benchmarks for equity schemes (Nifty 50 TRI, BSE Sensex TRI, Nifty Midcap 150 TRI), benchmarks for debt schemes (CRISIL indices, Nifty indices), benchmarks for hybrid and other schemes, quantitative measures of fund manager performance (alpha, information ratio, Jensen alpha), tracking error definition and calculation, tracking error importance for index funds and ETFs, scheme performance disclosure rules"},
]

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter   INTEGER NOT NULL,
            score     INTEGER NOT NULL,
            total     INTEGER NOT NULL,
            date      TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   INTEGER NOT NULL,
            question     TEXT NOT NULL,
            options      TEXT NOT NULL,
            correct_idx  INTEGER NOT NULL,
            selected_idx INTEGER NOT NULL,
            explanation  TEXT NOT NULL,
            topic        TEXT NOT NULL,
            is_correct   INTEGER NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    con.commit()
    con.close()

def save_session(chapter_id, score, total, questions_data):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO sessions (chapter, score, total, date) VALUES (?, ?, ?, ?)",
        (chapter_id, score, total, datetime.now().strftime("%d %b %Y, %I:%M %p"))
    )
    session_id = cur.lastrowid
    for q in questions_data:
        cur.execute("""
            INSERT INTO questions 
            (session_id, question, options, correct_idx, selected_idx, explanation, topic, is_correct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            q["question"],
            json.dumps(q["options"]),
            q["correctIndex"],
            q["selectedIndex"],
            q["explanation"],
            q["topic"],
            1 if q["selectedIndex"] == q["correctIndex"] else 0
        ))
    con.commit()
    con.close()
    return session_id

def get_all_sessions():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT s.id, s.chapter, s.score, s.total, s.date,
               (SELECT title FROM json_each('[]'))
        FROM sessions s
        ORDER BY s.id DESC
    """)
    # Simpler query
    cur.execute("SELECT id, chapter, score, total, date FROM sessions ORDER BY id DESC")
    rows = cur.fetchall()
    con.close()
    return rows

def get_session_questions(session_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT question, options, correct_idx, selected_idx, explanation, topic, is_correct
        FROM questions WHERE session_id = ? ORDER BY id
    """, (session_id,))
    rows = cur.fetchall()
    con.close()
    return rows

def get_chapter_stats():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT chapter, COUNT(*) as attempts, SUM(score) as total_score, SUM(total) as total_q
        FROM sessions GROUP BY chapter
    """)
    rows = cur.fetchall()
    con.close()
    return {r[0]: {"attempts": r[1], "score": r[2], "total": r[3]} for r in rows}

# ─────────────────────────────────────────────
# API — Google Gemini
# ─────────────────────────────────────────────
def generate_question(chapter, previous_topics):
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        st.error("⚠️ Please enter your Gemini API key in the sidebar.")
        return None

    if genai is None:
        st.error("⚠️ Package missing. Run: pip install google-generativeai")
        return None

    prev_str = ""
    if previous_topics:
        prev_str = f"\n\nAVOID repeating these topics already covered this session:\n{', '.join(previous_topics)}"

    prompt = f"""You are an expert NISM Series V-A exam question generator. Generate ONE multiple-choice question for Chapter {chapter['id']}: "{chapter['title']}".

Key topics in this chapter: {chapter['topics']}{prev_str}

Requirements:
- Question must test real exam-worthy knowledge from the chapter
- 4 options (A, B, C, D) — exactly one correct answer
- Options should be plausible but clearly distinguishable
- Include a clear explanation (2-3 sentences) of why the correct answer is right, and briefly why the others are wrong if relevant
- Cover a DIFFERENT specific topic/sub-topic each time
- Make questions practical and application-based, not just definitions

Respond ONLY with valid JSON (no markdown, no backticks):
{{
  "question": "question text here",
  "options": ["option A text", "option B text", "option C text", "option D text"],
  "correctIndex": 0,
  "explanation": "explanation text here",
  "topic": "brief topic tag e.g. NAV calculation"
}}"""

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"Error generating question: {e}")
        return None

# ─────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────
def inject_pwa():
    st.markdown("""
    <link rel="manifest" href="data:application/json;base64,eyJuYW1lIjoiTklTTSBWLUEgUXVpeiIsInNob3J0X25hbWUiOiJOSVNNIFF1aXoiLCJzdGFydF91cmwiOiIvIiwiZGlzcGxheSI6InN0YW5kYWxvbmUiLCJiYWNrZ3JvdW5kX2NvbG9yIjoiIzBkMGYxNCIsInRoZW1lX2NvbG9yIjoiI2Q0YTg0MyIsImRlc2NyaXB0aW9uIjoiTklTTSBTZXJpZXMgVi1BIE1vY2sgUXVpeiIsImljb25zIjpbeyJzcmMiOiJodHRwczovL2Ntcy5tYXRoLnVuaS1mcmFua2Z1cnQuZGUvaWNvbnMvZmF2aWNvbi5pY28iLCJzaXplcyI6IjI1NngyNTYiLCJ0eXBlIjoiaW1hZ2UveC1pY29uIn1dfQ==">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="NISM Quiz">
    <meta name="theme-color" content="#d4a843">
    """, unsafe_allow_html=True)


def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;600;700&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Crimson Pro', Georgia, serif; }

    .stApp { background-color: #0d0f14; }

    h1, h2, h3 { color: #f0e8d8 !important; font-family: 'Crimson Pro', serif !important; }

    .badge {
        display: inline-block;
        background: #1a1d24;
        border: 1px solid #d4a843;
        color: #d4a843;
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        letter-spacing: 2px;
        padding: 4px 14px;
        border-radius: 2px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .chapter-card {
        background: #1a1d24;
        border: 1px solid #2a2d35;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 10px;
        cursor: pointer;
        transition: border-color 0.2s;
    }

    .chapter-card:hover { border-color: #d4a843; }
    .chapter-card.done { border-color: #2d5a3d; background: #151c19; }

    .ch-num { font-family: 'DM Mono', monospace; font-size: 10px; color: #5a5a6a; letter-spacing: 1px; text-transform: uppercase; }
    .ch-title { font-size: 16px; font-weight: 700; color: #e0d8c8; margin-top: 2px; }
    .ch-score { font-family: 'DM Mono', monospace; font-size: 11px; color: #4a9a5a; margin-top: 4px; }

    .question-box {
        background: #1a1d24;
        border: 1px solid #2a2d35;
        border-radius: 8px;
        padding: 24px 28px;
        margin-bottom: 20px;
    }

    .q-label { font-family: 'DM Mono', monospace; font-size: 10px; color: #d4a843; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 12px; }
    .q-text  { font-size: 20px; font-weight: 700; color: #f0e8d8; line-height: 1.55; }

    .explanation-box {
        border-radius: 6px;
        padding: 16px 20px;
        margin-top: 16px;
        margin-bottom: 10px;
        border-left: 3px solid;
    }
    .explanation-box.correct { background: #151c19; border-color: #4a9a5a; }
    .explanation-box.wrong   { background: #1c1515; border-color: #9a3a3a; }

    .exp-label { font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }
    .exp-label.correct { color: #4a9a5a; }
    .exp-label.wrong   { color: #9a3a3a; }
    .exp-text  { font-size: 15px; color: #b8b0a0; line-height: 1.65; }

    .stat-box {
        background: #1a1d24;
        border: 1px solid #2a2d35;
        border-radius: 6px;
        padding: 14px 18px;
        text-align: center;
    }
    .stat-val   { font-size: 28px; font-weight: 700; color: #d4a843; }
    .stat-label { font-family: 'DM Mono', monospace; font-size: 10px; color: #5a5a6a; letter-spacing: 1px; text-transform: uppercase; margin-top: 4px; }

    .history-row {
        background: #1a1d24;
        border: 1px solid #2a2d35;
        border-radius: 6px;
        padding: 14px 20px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .review-q {
        background: #1a1d24;
        border: 1px solid #2a2d35;
        border-radius: 8px;
        padding: 20px 24px;
        margin-bottom: 14px;
    }
    .review-q.correct { border-left: 4px solid #4a9a5a; }
    .review-q.wrong   { border-left: 4px solid #9a3a3a; }

    .option-line { padding: 6px 0; font-size: 15px; color: #b8b0a0; }
    .option-line.correct-ans { color: #6aba7a; font-weight: 600; }
    .option-line.wrong-ans   { color: #ca6a6a; text-decoration: line-through; }

    .stButton > button {
        background: #1a1d24 !important;
        border: 1px solid #d4a843 !important;
        color: #d4a843 !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 12px !important;
        letter-spacing: 1.5px !important;
        border-radius: 5px !important;
        padding: 10px 24px !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: #d4a843 !important;
        color: #0d0f14 !important;
    }

    .stRadio > div { gap: 8px !important; }
    .stRadio label {
        background: #1a1d24 !important;
        border: 1px solid #2a2d35 !important;
        border-radius: 6px !important;
        padding: 12px 16px !important;
        color: #c8c0b0 !important;
        font-size: 16px !important;
        cursor: pointer !important;
        transition: border-color 0.15s !important;
        width: 100% !important;
    }
    .stRadio label:hover { border-color: #d4a843 !important; }

    .stTextInput input {
        background: #1a1d24 !important;
        border: 1px solid #2a2d35 !important;
        color: #e0d8c8 !important;
        border-radius: 5px !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 13px !important;
    }

    .stSelectbox select, [data-baseweb="select"] {
        background: #1a1d24 !important;
        color: #e0d8c8 !important;
        border-color: #2a2d35 !important;
    }

    [data-testid="stSidebar"] {
        background: #111318 !important;
        border-right: 1px solid #2a2d35 !important;
    }

    .stProgress > div > div { background: #d4a843 !important; }

    hr { border-color: #2a2d35 !important; }

    .stMarkdown p { color: #c8c0b0; font-size: 15px; line-height: 1.65; }

    div[data-testid="metric-container"] {
        background: #1a1d24;
        border: 1px solid #2a2d35;
        border-radius: 8px;
        padding: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_chapter_by_id(cid):
    return next((c for c in CHAPTERS if c["id"] == cid), None)

def pct_color(pct):
    if pct >= 80: return "🟢"
    if pct >= 50: return "🟡"
    return "🔴"

def reset_quiz():
    for k in ["quiz_chapter", "current_q", "q_num", "score",
              "selected", "answered", "session_qs", "session_done"]:
        if k in st.session_state:
            del st.session_state[k]

# ─────────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────────
def page_home():
    st.markdown('<div class="badge">NISM Series V-A</div>', unsafe_allow_html=True)
    st.markdown("## Mutual Fund Distributors — Mock Quiz")
    st.markdown("*5 questions per chapter · No negative marking · 50% to pass*")
    st.markdown("---")

    stats = get_chapter_stats()
    total_score   = sum(v["score"] for v in stats.values())
    total_q       = sum(v["total"] for v in stats.values())
    total_sessions = sum(v["attempts"] for v in stats.values())

    if total_sessions > 0:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="stat-box"><div class="stat-val">{total_score}/{total_q}</div><div class="stat-label">Total Score</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-box"><div class="stat-val">{len(stats)}/11</div><div class="stat-label">Chapters Attempted</div></div>', unsafe_allow_html=True)
        with c3:
            pct = round((total_score / total_q) * 100) if total_q else 0
            st.markdown(f'<div class="stat-box"><div class="stat-val">{pct}%</div><div class="stat-label">Overall Accuracy</div></div>', unsafe_allow_html=True)
        st.markdown("")

    st.markdown("### Select a Chapter")

    for ch in CHAPTERS:
        ch_stat = stats.get(ch["id"])
        done_class = "done" if ch_stat else ""
        score_html = ""
        if ch_stat:
            pct = round((ch_stat["score"] / ch_stat["total"]) * 100)
            score_html = f'<div class="ch-score">{pct_color(pct)} Best: {ch_stat["score"]}/{ch_stat["total"]} ({pct}%) · {ch_stat["attempts"]} attempt(s)</div>'

        st.markdown(f"""
        <div class="chapter-card {done_class}">
            <div class="ch-num">Chapter {ch['id']}</div>
            <div class="ch-title">{ch['emoji']} {ch['title']}</div>
            {score_html}
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"Start Ch {ch['id']}", key=f"start_{ch['id']}"):
            reset_quiz()
            st.session_state.quiz_chapter = ch["id"]
            st.session_state.page = "quiz"
            st.rerun()


def page_quiz():
    cid = st.session_state.get("quiz_chapter")
    chapter = get_chapter_by_id(cid)
    if not chapter:
        st.session_state.page = "home"
        st.rerun()

    # Init session state
    if "q_num" not in st.session_state:
        st.session_state.q_num = 1
        st.session_state.score = 0
        st.session_state.current_q = None
        st.session_state.selected = None
        st.session_state.answered = False
        st.session_state.session_qs = []
        st.session_state.session_done = False

    # Back button
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Back"):
            reset_quiz()
            st.session_state.page = "home"
            st.rerun()
    with col_title:
        st.markdown(f"### {chapter['emoji']} {chapter['title']}")

    # Session complete
    if st.session_state.session_done:
        final_score = st.session_state.score
        pct = round((final_score / QUESTIONS_PER_SESSION) * 100)
        st.markdown("---")
        st.markdown(f'<div class="stat-box"><div class="stat-val">{final_score}/{QUESTIONS_PER_SESSION}</div><div class="stat-label">Chapter {cid} Complete — {pct}%</div></div>', unsafe_allow_html=True)
        st.markdown("")

        if pct == 100:
            st.success("🎯 Perfect score! Excellent preparation.")
        elif pct >= 80:
            st.success("Very strong performance. Keep it up!")
        elif pct >= 60:
            st.warning("Good effort. Review the missed questions.")
        else:
            st.error("Needs more revision on this chapter.")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔄 Retry Chapter"):
                reset_quiz()
                st.session_state.quiz_chapter = cid
                st.session_state.page = "quiz"
                st.rerun()
        with c2:
            if st.button("📚 All Chapters"):
                reset_quiz()
                st.session_state.page = "home"
                st.rerun()
        with c3:
            if st.button("📊 View History"):
                reset_quiz()
                st.session_state.page = "history"
                st.rerun()
        return

    # Progress
    q_num = st.session_state.q_num
    score = st.session_state.score
    st.progress(((q_num - 1) / QUESTIONS_PER_SESSION))
    st.markdown(f'<p style="font-family:\'DM Mono\',monospace;font-size:11px;color:#5a5a6a;letter-spacing:1px;">QUESTION {q_num} / {QUESTIONS_PER_SESSION} &nbsp;·&nbsp; SCORE {score}</p>', unsafe_allow_html=True)

    # Generate question if needed
    if st.session_state.current_q is None:
        with st.spinner("Generating question from workbook..."):
            prev_topics = [q["topic"] for q in st.session_state.session_qs]
            q = generate_question(chapter, prev_topics)
            if q is None:
                return
            st.session_state.current_q = q
            st.session_state.selected = None
            st.session_state.answered = False

    q = st.session_state.current_q

    # Question box
    st.markdown(f"""
    <div class="question-box">
        <div class="q-label">Question {q_num}</div>
        <div class="q-text">{q['question']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Options
    option_labels = [f"{chr(65+i)}. {opt}" for i, opt in enumerate(q["options"])]

    if not st.session_state.answered:
        selected_label = st.radio("Choose your answer:", option_labels, key=f"radio_{q_num}", label_visibility="collapsed")
        selected_idx = option_labels.index(selected_label) if selected_label else 0

        if st.button("Submit Answer →"):
            st.session_state.selected = selected_idx
            st.session_state.answered = True
            is_correct = selected_idx == q["correctIndex"]
            if is_correct:
                st.session_state.score += 1

            # Save question to session
            st.session_state.session_qs.append({
                "question": q["question"],
                "options": q["options"],
                "correctIndex": q["correctIndex"],
                "selectedIndex": selected_idx,
                "explanation": q["explanation"],
                "topic": q["topic"]
            })

            # If last question, save to DB
            if q_num >= QUESTIONS_PER_SESSION:
                save_session(cid, st.session_state.score, QUESTIONS_PER_SESSION, st.session_state.session_qs)
                st.session_state.session_done = True

            st.rerun()
    else:
        # Show answered state
        sel = st.session_state.selected
        correct = q["correctIndex"]
        is_correct = sel == correct

        for i, opt in enumerate(q["options"]):
            if i == correct:
                st.markdown(f'<div class="option-line correct-ans">✓ {chr(65+i)}. {opt}</div>', unsafe_allow_html=True)
            elif i == sel and not is_correct:
                st.markdown(f'<div class="option-line wrong-ans">✗ {chr(65+i)}. {opt}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="option-line">&nbsp;&nbsp;{chr(65+i)}. {opt}</div>', unsafe_allow_html=True)

        # Explanation
        cls = "correct" if is_correct else "wrong"
        label = "✓ Correct!" if is_correct else "✗ Incorrect"
        st.markdown(f"""
        <div class="explanation-box {cls}">
            <div class="exp-label {cls}">{label}</div>
            <div class="exp-text">{q['explanation']}</div>
        </div>
        """, unsafe_allow_html=True)

        btn_label = "See Results →" if q_num >= QUESTIONS_PER_SESSION else "Next Question →"
        if st.button(btn_label):
            if q_num < QUESTIONS_PER_SESSION:
                st.session_state.q_num += 1
                st.session_state.current_q = None
                st.rerun()
            else:
                st.session_state.session_done = True
                st.rerun()


def page_history():
    st.markdown("## 📊 Exam History")
    st.markdown("---")

    if st.button("← Back to Chapters"):
        st.session_state.page = "home"
        st.rerun()

    sessions = get_all_sessions()
    if not sessions:
        st.info("No exam sessions saved yet. Complete a chapter quiz to see your history here.")
        return

    stats = get_chapter_stats()
    st.markdown(f"**{len(sessions)} total session(s) across {len(stats)} chapter(s)**")
    st.markdown("")

    # Chapter filter
    chapter_options = ["All Chapters"] + [f"Chapter {c['id']}: {c['title']}" for c in CHAPTERS]
    filter_ch = st.selectbox("Filter by chapter:", chapter_options)
    filter_id = None
    if filter_ch != "All Chapters":
        filter_id = int(filter_ch.split(":")[0].replace("Chapter ", "").strip())

    st.markdown("")

    for sess in sessions:
        sid, ch_id, score, total, date = sess
        if filter_id and ch_id != filter_id:
            continue
        chapter = get_chapter_by_id(ch_id)
        pct = round((score / total) * 100)
        icon = pct_color(pct)
        ch_name = chapter["title"] if chapter else f"Chapter {ch_id}"

        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"""
            **{icon} Ch {ch_id}: {ch_name}** &nbsp;·&nbsp; 
            <span style="color:#d4a843;font-family:'DM Mono',monospace;font-size:13px">{score}/{total} ({pct}%)</span> &nbsp;·&nbsp;
            <span style="color:#5a5a6a;font-family:'DM Mono',monospace;font-size:11px">{date}</span>
            """, unsafe_allow_html=True)
        with col2:
            if st.button("Review", key=f"review_{sid}"):
                st.session_state.review_session_id = sid
                st.session_state.page = "review"
                st.rerun()

        st.markdown('<hr style="margin:8px 0;border-color:#1a1d24">', unsafe_allow_html=True)


def page_review():
    sid = st.session_state.get("review_session_id")
    if not sid:
        st.session_state.page = "history"
        st.rerun()

    # Get session info
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT chapter, score, total, date FROM sessions WHERE id=?", (sid,))
    sess = cur.fetchone()
    con.close()

    if not sess:
        st.session_state.page = "history"
        st.rerun()

    ch_id, score, total, date = sess
    chapter = get_chapter_by_id(ch_id)
    pct = round((score / total) * 100)

    if st.button("← Back to History"):
        st.session_state.page = "history"
        st.rerun()

    st.markdown(f"## 🔖 Review — {chapter['emoji']} {chapter['title']}")
    st.markdown(f'<p style="font-family:\'DM Mono\',monospace;font-size:12px;color:#5a5a6a">{date} &nbsp;·&nbsp; Score: {score}/{total} ({pct}%) &nbsp;·&nbsp; {pct_color(pct)}</p>', unsafe_allow_html=True)
    st.markdown("---")

    rows = get_session_questions(sid)
    for i, row in enumerate(rows, 1):
        question, options_json, correct_idx, selected_idx, explanation, topic, is_correct = row
        options = json.loads(options_json)
        cls = "correct" if is_correct else "wrong"
        result_icon = "✓" if is_correct else "✗"

        st.markdown(f"""
        <div class="review-q {cls}">
            <div class="q-label">Q{i} &nbsp;·&nbsp; {topic} &nbsp;·&nbsp; {'✓ Correct' if is_correct else '✗ Incorrect'}</div>
            <div class="q-text" style="font-size:17px;margin-bottom:14px">{question}</div>
        """, unsafe_allow_html=True)

        for j, opt in enumerate(options):
            if j == correct_idx and j == selected_idx:
                st.markdown(f'<div class="option-line correct-ans">✓ {chr(65+j)}. {opt} ← Your answer (Correct)</div>', unsafe_allow_html=True)
            elif j == correct_idx:
                st.markdown(f'<div class="option-line correct-ans">✓ {chr(65+j)}. {opt} ← Correct answer</div>', unsafe_allow_html=True)
            elif j == selected_idx:
                st.markdown(f'<div class="option-line wrong-ans">✗ {chr(65+j)}. {opt} ← Your answer</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="option-line">&nbsp;&nbsp;{chr(65+j)}. {opt}</div>', unsafe_allow_html=True)

        exp_cls = "correct" if is_correct else "wrong"
        st.markdown(f"""
            <div class="explanation-box {exp_cls}" style="margin-top:12px">
                <div class="exp-label {exp_cls}">📝 Explanation</div>
                <div class="exp-text">{explanation}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown('<div class="badge">NISM V-A</div>', unsafe_allow_html=True)
        st.markdown("### Settings")
        st.markdown("---")

        api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.get("api_key", ""),
            type="password",
            help="Free key from aistudio.google.com — no card needed"
        )
        st.session_state.api_key = api_key

        if not api_key:
            st.markdown("""
            <div style="background:#1e2010;border:1px solid #4a6a1a;border-radius:5px;padding:10px 12px;font-size:12px;color:#8aba4a;font-family:'DM Mono',monospace;line-height:1.7">
            🔑 Get free API key:<br>
            1. Go to aistudio.google.com<br>
            2. Sign in with Google<br>
            3. Click "Get API Key"<br>
            4. Paste it above
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#4a9a5a;font-family:\'DM Mono\',monospace;font-size:11px">✓ API key set</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Navigation**")

        if st.button("🏠 Home", use_container_width=True):
            reset_quiz()
            st.session_state.page = "home"
            st.rerun()

        if st.button("📊 History", use_container_width=True):
            reset_quiz()
            st.session_state.page = "history"
            st.rerun()

        st.markdown("---")
        st.markdown("""
        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#3a3d45;line-height:1.8">
        100 MCQs · 2 hours<br>
        50% passing score<br>
        No negative marking<br>
        <br>
        Data saved locally in<br>
        <code style="color:#d4a843">nism_quiz_results.db</code>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="NISM V-A Mock Quiz",
        page_icon="📘",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    init_db()
    inject_pwa()
    inject_css()

    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    sidebar()

    page = st.session_state.page
    if page == "home":
        page_home()
    elif page == "quiz":
        page_quiz()
    elif page == "history":
        page_history()
    elif page == "review":
        page_review()


if __name__ == "__main__":
    main()
