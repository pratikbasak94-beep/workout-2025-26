"""
NISM Series V-A — Mock Quiz & PDF Notes App
Requirements: pip install streamlit google-generativeai fpdf2
Run: streamlit run nism_quiz_app.py
"""

import streamlit as st
import sqlite3
import json
import os
import threading
import time
from datetime import datetime, timedelta

from fpdf import FPDF

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
DB_PATH = "nism_quiz_results.db"
QUESTIONS_PER_SESSION = 10      
SPECIAL_TEST_QS = 30            
SPECIAL_TEST_MINS = 36          

# UPDATED: Using the Gemini 2.5 and 2.0 models to ensure API access
GEMINI_MODELS = [
    {"label": "Gemini 2.5 Flash Lite (Fastest & Free)", "id": "gemini-2.5-flash-lite"},
    {"label": "Gemini 2.5 Flash (Balanced)",            "id": "gemini-2.5-flash"},
    {"label": "Gemini 2.0 Flash (Fallback)",            "id": "gemini-2.0-flash"},
    {"label": "Gemini 2.5 Pro (Deep Reasoning)",        "id": "gemini-2.5-pro"}
]

CHAPTERS = [
    {"id": 1,  "title": "Investment Landscape", "emoji": "🌐",
     "topics": "financial goals, savings vs investment, asset classes (equity/debt/real estate/commodities/gold), investment risks (market/credit/liquidity/inflation/interest rate), risk measures (standard deviation, beta, VaR), behavioural biases (anchoring, recency, herding, confirmation, mental accounting, overconfidence, loss aversion, endowment effect), risk profiling, asset allocation strategies, do-it-yourself vs professional help"},
    {"id": 2,  "title": "Concept & Role of a Mutual Fund", "emoji": "🏦",
     "topics": "mutual fund definition and concept, pooling of funds, NAV, diversification, professional management, types by structure (open-ended, close-ended, interval), by asset class (equity, debt, hybrid, solution-oriented), sub-categories of equity (large cap, mid cap, small cap, multi cap, flexi cap, ELSS, sectoral, thematic, index, ETF), debt categories (liquid, overnight, ultra short, short/medium/long duration, dynamic bond, gilt, credit risk, corporate bond), hybrid categories (conservative, balanced, aggressive, dynamic asset allocation, multi-asset, arbitrage), growth of MF industry in India, AUM trends, SIP"},
    {"id": 3,  "title": "Legal Structure of Mutual Funds", "emoji": "⚖️",
     "topics": "three-tier structure (sponsor, trust/trustees, AMC), role of sponsor, trust deed, role of trustees, obligations of trustees, AMC registration, role of AMC, restrictions on AMC, service providers: RTA, custodian, depository, auditors, fund accountants, role and function of AMFI, AMFI code of conduct, AMFI Registration Number (ARN), organization structure of AMC"},
    {"id": 4,  "title": "Legal & Regulatory Framework", "emoji": "📋",
     "topics": "SEBI Act 1992, SEBI (Mutual Funds) Regulations 1996, SEBI regulatory role, AMFI, RBI role for liquid funds, stock exchange listing of close-ended funds, SEBI circulars and guidelines, scheme categorization and rationalization, investor grievance redressal mechanism, SCORES platform, SEBI Ombudsman, due diligence by AMCs for distributors, AMFI code of conduct for intermediaries, risk-o-meter, side pocketing rules, swing pricing, segregated portfolio"},
    {"id": 5,  "title": "Scheme Related Information", "emoji": "📄",
     "topics": "Scheme Information Document (SID), Statement of Additional Information (SAI), Key Information Memorandum (KIM), addendum, contents of SID, investment objective, asset allocation pattern, investment strategies, risk factors, benchmark, fund manager details, expense ratio disclosure, load structure, SID filing with SEBI, product labelling, risk-o-meter, potential risk class matrix for debt funds"},
    {"id": 6,  "title": "Fund Distribution & Channel Management", "emoji": "📊",
     "topics": "role of mutual fund distributor, individual vs institutional distributors, banks as distributors, online platforms, MFD vs RIA, direct plan vs regular plan, ARN registration, EUIN, AMFI certification, trail commission vs upfront commission, TER limits, commission disclosure by SEBI, due diligence by AMC, distributor empanelment, change of distributor, nomination facility for distributors, difference between distributor and investment adviser, execution-only platform (EOP)"},
    {"id": 7,  "title": "NAV, TER & Pricing of Units", "emoji": "🔢",
     "topics": "fair valuation principles, mark-to-market valuation, amortization of debt securities, valuation of non-traded securities, NAV calculation formula (assets minus liabilities divided by units), accrual of income and expenses, NAV computation frequency, declaration of NAV, Total Expense Ratio (TER) components, TER limits for equity and debt schemes, daily TER disclosure, entry load (abolished), exit load, impact of exit load on NAV, accounting standards for mutual funds, annual report and financial statements, segregated portfolio NAV and TER"},
    {"id": 8,  "title": "Taxation", "emoji": "💰",
     "topics": "capital gains taxation for equity funds (LTCG above Rs 1.25 lakh at 12.5%, STCG at 20%), capital gains for debt funds (taxed as per income slab after April 2023), IDCW taxed as income, DDT abolished, stamp duty on purchase at 0.005%, setting off capital gains and losses, STT on equity fund redemptions, ELSS tax benefit under Section 80C up to Rs 1.5 lakh, TDS on capital gains for NRI investors, GST on AMC fees, indexation benefit removed for debt funds after 2023 Finance Act"},
    {"id": 9,  "title": "Investor Services", "emoji": "🧾",
     "topics": "NFO process, NFO price Rs 10, ongoing NAV-based pricing, SIP (Systematic Investment Plan), SWP (Systematic Withdrawal Plan), STP (Systematic Transfer Plan), growth option vs IDCW option, dividend payout vs dividend reinvestment, folio number, account statement (CAS), KYC process (CKYC, in-person verification), PAN requirement, minor investors, NRI investors, joint holding, nomination, filling application form, redemption process, cut-off times (liquid fund 1:30 PM, other funds 3 PM), time stamping, turnaround times (T+3 for redemption), SIP registration, SIP auto-debit, switch transaction, transmission of units"},
    {"id": 10, "title": "Risk, Return & Performance of Funds", "emoji": "📈",
     "topics": "types of risk (systematic vs unsystematic, market/credit/liquidity/interest rate/concentration/reinvestment risk), modified duration and interest rate risk, credit rating and credit risk, portfolio diversification, drivers of return in equity and debt funds, measures of return (absolute return, annualised return, CAGR, XIRR, rolling returns, trailing returns), SEBI norms on return representation, standard deviation, beta, Sharpe ratio, Sortino ratio, Treynor ratio, alpha, R-squared, maximum drawdown, credit risk provisions, side pocketing"},
    {"id": 11, "title": "Mutual Fund Scheme Performance", "emoji": "🎯",
     "topics": "benchmarks and their importance, Price Return Index (PRI) vs Total Return Index (TRI), SEBI mandate for TRI benchmarks, choosing appropriate benchmark, benchmarks for equity schemes (Nifty 50 TRI, BSE Sensex TRI, Nifty Midcap 150 TRI), benchmarks for debt schemes (CRISIL indices, Nifty indices), benchmarks for hybrid and other schemes, quantitative measures of fund manager performance (alpha, information ratio, Jensen alpha), tracking error definition and calculation, tracking error importance for index funds and ETFs, scheme performance disclosure rules"},
{"id": 12, "title": "Mutual Fund Scheme Selection", "emoji": "🎯",
     "topics": "scheme selection based on investor needs/risk profile, risk-return hierarchy of fund categories, active vs passive funds, diversified vs sector/thematic funds, evaluating fund performance (age, size, turnover, expenses), selecting between AMCs and options, growth vs value investment strategies"}]

# ─────────────────────────────────────────────
# PDF GENERATOR CLASS
# ─────────────────────────────────────────────
class StyledPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "NISM Prep Portal - Detailed Study Notes", align="R")
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def create_pdf_bytes(markdown_text):
    pdf = StyledPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    clean_markdown = markdown_text.replace('---', '').replace('***', '').replace('___', '')
    lines = clean_markdown.split('\n')
    
    for line in lines:
        line = line.strip()
        line = line.replace('\xa0', ' ').replace('\t', ' ')
        line = line.encode('latin-1', 'replace').decode('latin-1')

        if not line:
            pdf.ln(5)
            continue
            
        try:
            if line.startswith("#"):
                clean_text = line.replace("#", "").strip()
                pdf.set_font("helvetica", "B", 16)
                pdf.set_text_color(0, 51, 102)
                pdf.multi_cell(0, 10, clean_text)
                pdf.ln(2)
            elif line.startswith("-") or line.startswith("*"):
                clean_text = line[1:].replace("**", "").strip()
                pdf.set_font("helvetica", "", 12)
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(0, 8, f"-  {clean_text}") 
            else:
                clean_text = line.replace("**", "")
                pdf.set_font("helvetica", "", 12)
                pdf.set_text_color(40, 40, 40)
                pdf.multi_cell(0, 7, clean_text)
        except Exception:
            pass
            
    return bytes(pdf.output())

def build_exam_pdf_content(session_id, username):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT chapter, score, total, date FROM sessions WHERE id=?", (session_id,))
    sess = cur.fetchone()
    
    if not sess:
        con.close()
        return None

    ch_id, score, total, date = sess
    chapter = get_chapter_by_id(ch_id)
    
    cur.execute("SELECT question, options, correct_idx, selected_idx, explanation, topic, is_correct FROM questions WHERE session_id = ? ORDER BY id", (session_id,))
    rows = cur.fetchall()
    con.close()

    pdf = StyledPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(0, 51, 102)
    
    exam_title = "NISM Series V-A — Special 30-Mark Scorecard" if total == 30 else "NISM Series V-A — Mock Exam Scorecard"
    pdf.multi_cell(0, 10, exam_title, align="C")
    pdf.ln(5)

    pct = round((score/total)*100)
    pdf.set_font("helvetica", "", 12)
    pdf.set_text_color(40, 40, 40)
    
    pdf.multi_cell(0, 8, f"Student: {username.upper()}")
    pdf.multi_cell(0, 8, f"Chapter: {ch_id}. {chapter['title']}")
    pdf.multi_cell(0, 8, f"Date: {date}")
    pdf.set_font("helvetica", "B", 12)
    pdf.multi_cell(0, 8, f"Final Score: {score} / {total}  ({pct}%)")
    pdf.ln(10)

    for i, row in enumerate(rows, 1):
        question, options_json, correct_idx, selected_idx, explanation, topic, is_correct = row
        options = json.loads(options_json)
        result_text = "CORRECT" if is_correct else "INCORRECT"

        question = question.replace('\xa0', ' ').encode('latin-1', 'replace').decode('latin-1')
        explanation = explanation.replace('\xa0', ' ').encode('latin-1', 'replace').decode('latin-1')
        topic = topic.replace('\xa0', ' ').encode('latin-1', 'replace').decode('latin-1')

        try:
            pdf.set_font("helvetica", "B", 12)
            if is_correct:
                pdf.set_text_color(34, 139, 34) 
            else:
                pdf.set_text_color(220, 20, 60) 
            pdf.multi_cell(0, 8, f"Q{i}. [{topic}] — {result_text}")

            pdf.set_font("helvetica", "B", 12)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 7, question)
            pdf.ln(3)

            pdf.set_font("helvetica", "", 11)
            for j, opt in enumerate(options):
                opt = opt.replace('\xa0', ' ').encode('latin-1', 'replace').decode('latin-1')
                
                if j == correct_idx and j == selected_idx:
                    pdf.set_text_color(34, 139, 34) 
                    prefix = "-> (YOURS & CORRECT)"
                elif j == correct_idx:
                    pdf.set_text_color(34, 139, 34) 
                    prefix = "-> (CORRECT ANSWER)"
                elif j == selected_idx:
                    pdf.set_text_color(220, 20, 60) 
                    prefix = "-> (YOUR ANSWER)"
                else:
                    pdf.set_text_color(80, 80, 80)  
                    prefix = "   "
                    
                pdf.multi_cell(0, 6, f"{chr(65+j)}. {prefix}  {opt}")
            
            pdf.ln(3)
            pdf.set_font("helvetica", "I", 11)
            pdf.set_text_color(100, 100, 100) 
            pdf.multi_cell(0, 6, f"Explanation: {explanation}")
            pdf.ln(10)
        except Exception:
            pdf.write(8, "[Error formatting this specific question block]\n\n")

    return bytes(pdf.output())

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL DEFAULT 'Guest',
            chapter INTEGER NOT NULL,
            score   INTEGER NOT NULL,
            total   INTEGER NOT NULL,
            date    TEXT NOT NULL
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
    
    cur.execute("PRAGMA table_info(sessions)")
    columns = [info[1] for info in cur.fetchall()]
    if "username" not in columns:
        cur.execute("ALTER TABLE sessions ADD COLUMN username TEXT NOT NULL DEFAULT 'Guest'")
        
    con.commit()
    con.close()

def save_session(username, chapter_id, score, total, questions_data):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO sessions (username, chapter, score, total, date) VALUES (?, ?, ?, ?, ?)",
        (username, chapter_id, score, total, datetime.now().strftime("%d %b %Y, %I:%M %p"))
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

def get_all_sessions(username):
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("SELECT id, chapter, score, total, date FROM sessions WHERE username = ? ORDER BY id DESC", (username,))
        rows = cur.fetchall()
        con.close()
        return rows
    except Exception:
        return []

def get_session_questions(session_id):
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT question, options, correct_idx, selected_idx, explanation, topic, is_correct
            FROM questions WHERE session_id = ? ORDER BY id
        """, (session_id,))
        rows = cur.fetchall()
        con.close()
        return rows
    except Exception:
        return []

def get_chapter_stats(username):
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT chapter, COUNT(*) as attempts, SUM(score) as total_score, SUM(total) as total_q
            FROM sessions WHERE username = ? GROUP BY chapter
        """, (username,))
        rows = cur.fetchall()
        con.close()
        return {r[0]: {"attempts": r[1], "score": r[2], "total": r[3]} for r in rows}
    except Exception:
        return {}

# ─────────────────────────────────────────────
# WORKBOOK LOADER
# ─────────────────────────────────────────────
WORKBOOK_PATH = "workbook.txt"

CHAPTER_MARKERS = {
    1:  "CHAPTER 1: INVESTMENT LANDSCAPE",
    2:  "CHAPTER 2: CONCEPT AND ROLE OF A MUTUAL FUND",
    3:  "CHAPTER 3: LEGAL STRUCTURE OF MUTUAL FUNDS IN INDIA",
    4:  "CHAPTER 4: LEGAL AND REGULATORY FRAMEWORK",
    5:  "CHAPTER 5: SCHEME RELATED INFORMATION",
    6:  "CHAPTER 6: FUND DISTRIBUTION AND CHANNEL MANAGEMENT PRACTICES",
    7:  "CHAPTER 7: NET ASSET VALUE, TOTAL EXPENSE RATIO AND PRICING OF UNITS",
    8:  "CHAPTER 8: TAXATION",
    9:  "CHAPTER 9: INVESTOR SERVICES",
    10: "CHAPTER 10: RISK, RETURN AND PERFORMANCE OF FUNDS",
    11: "CHAPTER 11: MUTUAL FUND SCHEME PERFORMANCE",
}

@st.cache_resource
def load_workbook():
    if not os.path.exists(WORKBOOK_PATH):
        return None
    try:
        with open(WORKBOOK_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None

def get_chapter_text(chapter_id, max_chars=12000): 
    workbook = load_workbook()
    if not workbook:
        return None

    marker = CHAPTER_MARKERS.get(chapter_id, "").upper()
    next_marker = CHAPTER_MARKERS.get(chapter_id + 1, "").upper()
    upper_wb = workbook.upper()
    start = upper_wb.find(marker)
    if start == -1: return None

    if next_marker:
        end = upper_wb.find(next_marker, start + 100)
        chapter_text = workbook[start:end] if end != -1 else workbook[start:start + 25000]
    else:
        chapter_text = workbook[start:start + 25000]

    if len(chapter_text) > max_chars:
        chapter_text = chapter_text[500:500 + max_chars]
    return chapter_text.strip()

# ─────────────────────────────────────────────
# API — Google Gemini
# ─────────────────────────────────────────────
def _build_prompt(chapter, previous_topics, is_special=False):
    prev_str = ""
    if previous_topics:
        prev_str = f"\n\nAVOID repeating these topics already covered this session:\n{', '.join(previous_topics)}"

    workbook_text = get_chapter_text(chapter["id"], max_chars=4000)
    if workbook_text:
        context_section = f"""
Use the following ACTUAL TEXT from the NISM Series V-A workbook (November 2025 edition) to base your question on:
--- WORKBOOK EXCERPT (Chapter {chapter['id']}) ---
{workbook_text}
--- END EXCERPT ---
Base your question strictly on facts, figures, rules, and concepts present in this excerpt."""
    else:
        context_section = f"\nKey topics in this chapter: {chapter['topics']}"

    diff_str = "- Difficulty: Standard NISM V-A exam level."
    if is_special:
        diff_str = "- DIFFICULTY: HARD. Match the official NISM V-A exam standard strictly. Create scenario-based questions, tricky plausible distractors, and require advanced conceptual application."

    return f"""You are an expert NISM Series V-A exam question generator. Generate ONE multiple-choice question for Chapter {chapter['id']}: "{chapter['title']}".
{context_section}{prev_str}

Requirements:
{diff_str}
- 4 options (A, B, C, D) — exactly one correct answer
- Include a clear explanation (2-3 sentences)
- Cover a DIFFERENT specific topic/sub-topic each time

Respond ONLY with valid JSON (no markdown, no backticks):
{{
  "question": "question text here",
  "options": ["option A text", "option B text", "option C text", "option D text"],
  "correctIndex": 0,
  "explanation": "explanation text here",
  "topic": "brief topic tag"
}}"""

def _call_gemini_json(api_key, prompt):
    genai.configure(api_key=api_key)
    selected_id = st.session_state.get("selected_model", GEMINI_MODELS[0]["id"])
    ordered = [m for m in GEMINI_MODELS if m["id"] == selected_id]
    ordered += [m for m in GEMINI_MODELS if m["id"] != selected_id]

    last_error = None
    for m in ordered:
        try:
            model = genai.GenerativeModel(m["id"])
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                text = text.rsplit("```", 1)[0].strip()
            result = json.loads(text)
            
            if m["id"] != selected_id:
                st.session_state["active_model_used"] = m["label"]
            else:
                st.session_state["active_model_used"] = None
            return result
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err or "rate" in err or "exhausted" in err:
                last_error = f"{m['label']}: rate limited"
                time.sleep(2)
                continue
            else:
                raise e

    raise Exception(f"All models hit rate limits. Try again in a minute.\nDetails: {last_error}")

def generate_question(chapter, previous_topics, is_special=False):
    api_key = st.session_state.get("api_key", "")
    if not api_key: return None
    try:
        return _call_gemini_json(api_key, _build_prompt(chapter, previous_topics, is_special))
    except Exception as e:
        st.error(f"Error generating question: {e}")
        return None

def _preload_bg(api_key, chapter, previous_topics, store_key, is_special):
    if not api_key or genai is None: return
    try:
        result = _call_gemini_json(api_key, _build_prompt(chapter, previous_topics, is_special))
        st.session_state[store_key] = result
    except Exception:
        pass

def start_preload(chapter, previous_topics, store_key, is_special=False):
    if store_key in st.session_state: return
    st.session_state[store_key] = None
    api_key = st.session_state.get("api_key", "")
    t = threading.Thread(
        target=_preload_bg,
        args=(api_key, chapter, previous_topics, store_key, is_special),
        daemon=True
    )
    t.start()

def preload_key(ch_id, q_num):
    return f"preload_ch{ch_id}_q{q_num}"

# ─────────────────────────────────────────────
# MILITARY-GRADE ANTI-SKELETON PROMPT
# ─────────────────────────────────────────────
def _build_notes_prompt(chapter):
    workbook_text = get_chapter_text(chapter["id"], max_chars=15000) 
    if workbook_text:
        context_section = f"--- WORKBOOK TEXT EXCERPT ---\n{workbook_text}\n--- END EXCERPT ---"
    else:
        context_section = f"MANDATORY TOPICS TO COVER:\n{chapter['topics']}"

    return f"""You are a master Indian financial instructor writing a highly detailed textbook chapter for the NISM Series V-A exam.
You are writing Chapter {chapter['id']}: "{chapter['title']}".

Context to use:
{context_section}

CRITICAL RULES - READ CAREFULLY:
1. WRITE FULL PARAGRAPHS: For EVERY single topic listed above, you MUST write a minimum of a 4-sentence paragraph explaining what it is, how it works in the real world, and a financial example.
2. NO BLANK HEADINGS: You are strictly forbidden from writing a heading and leaving it blank. Every heading must be followed by dense, explanatory text.
3. NO LAZY LISTS: Do not just list terms like "Systematic Risk" and skip to the next line. You must explain it deeply so a beginner can pass a regulatory exam.
4. Extract exact SEBI rules, tax percentages, and cutoff times if applicable.
5. Format with Markdown headings (##) and bold text (**) for key terms.

Begin writing the comprehensive, dense textbook chapter now. Do not skip any topics."""

def generate_chapter_notes(chapter):
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        st.error("⚠️ Please enter your Gemini API key in the sidebar.")
        return None
        
    genai.configure(api_key=api_key)
    selected_id = st.session_state.get("selected_model", GEMINI_MODELS[0]["id"])
    ordered = [m for m in GEMINI_MODELS if m["id"] == selected_id]
    ordered += [m for m in GEMINI_MODELS if m["id"] != selected_id]

    for m in ordered:
        try:
            model = genai.GenerativeModel(m["id"])
            response = model.generate_content(_build_notes_prompt(chapter))
            return response.text
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err or "rate" in err or "exhausted" in err:
                time.sleep(2)
                continue
            else:
                st.error(f"Error generating notes: {e}")
                return None
    st.error("All AI models hit rate limits. Please wait a minute and try again.")
    return None

def get_chapter_by_id(cid):
    return next((c for c in CHAPTERS if c["id"] == cid), None)

def pct_color(pct):
    if pct >= 80: return "🟢"
    if pct >= 50: return "🟡"
    return "🔴"

def reset_quiz():
    for k in ["quiz_chapter", "current_q", "q_num", "score",
              "selected", "answered", "session_qs", "session_done", 
              "is_special_test", "exam_start_time", "exam_end_time"]:
        if k in st.session_state:
            del st.session_state[k]

# ─────────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────────
def page_login():
    st.markdown("## 🔐 Welcome to NISM Prep Portal")
    st.markdown("Enter your Name or Access Code to track your progress and unlock Special Exams.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        username_input = st.text_input("Username / Access Code", key="login_input")
        if st.button("Access Portal", use_container_width=True):
            if username_input.strip():
                st.session_state.username = username_input.strip()
                st.session_state.page = "home"
                st.rerun()
            else:
                st.error("Please enter a valid name.")
                
    st.markdown("---")
    st.markdown("*Note: Progress is saved uniquely to the name you enter here.*")

def page_home():
    username = st.session_state.username
    st.markdown(f"## Welcome back, {username} 👋")
    st.markdown("*10 questions per chapter · No negative marking*")
    st.markdown("---")

    stats = get_chapter_stats(username)
    total_score = sum(v["score"] for v in stats.values())
    total_q = sum(v["total"] for v in stats.values())
    total_sessions = sum(v["attempts"] for v in stats.values())
    global_pct = round((total_score / total_q) * 100) if total_q else 0

    if total_sessions > 0:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="stat-box"><div class="stat-val">{total_score}/{total_q}</div><div class="stat-label">Total Score</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-box"><div class="stat-val">{len(stats)}/11</div><div class="stat-label">Chapters Attempted</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-box"><div class="stat-val">{global_pct}%</div><div class="stat-label">Overall Accuracy</div></div>', unsafe_allow_html=True)
        st.markdown("")

    is_master_unlocked = (total_sessions >= 10 and global_pct >= 75)
    
    if is_master_unlocked:
        st.markdown("""
        <div style="background:#1e2010;border:1px solid #d4a843;border-radius:5px;padding:12px;margin-bottom:15px;">
        <span style="color:#d4a843;font-weight:bold;">🏆 ELITE ACCESS UNLOCKED</span><br>
        <span style="color:#c8c0b0;font-size:14px;">You have maintained a 75%+ average across 10+ exams. The Official NISM 30-Mark Timed Exams are now available for all chapters below!</span>
        </div>
        """, unsafe_allow_html=True)

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

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(f"Start Standard (10 Qs)", key=f"start_{ch['id']}"):
                reset_quiz()
                st.session_state.quiz_chapter = ch["id"]
                st.session_state.is_special_test = False
                st.session_state.page = "quiz"
                st.rerun()
                
        with col2:
            if is_master_unlocked:
                if st.button(f"⭐ Start Special Exam (30 Qs)", key=f"special_{ch['id']}"):
                    reset_quiz()
                    st.session_state.quiz_chapter = ch["id"]
                    st.session_state.is_special_test = True
                    st.session_state.page = "quiz"
                    st.rerun()

def page_quiz():
    cid = st.session_state.get("quiz_chapter")
    username = st.session_state.username
    is_special = st.session_state.get("is_special_test", False)
    target_qs = SPECIAL_TEST_QS if is_special else QUESTIONS_PER_SESSION
    
    chapter = get_chapter_by_id(cid)
    if not chapter:
        st.session_state.page = "home"
        st.rerun()

    if "q_num" not in st.session_state:
        st.session_state.q_num = 1
        st.session_state.score = 0
        st.session_state.current_q = None
        st.session_state.selected = None
        st.session_state.answered = False
        st.session_state.session_qs = []
        st.session_state.session_done = False
        
        if is_special:
            st.session_state.exam_start_time = datetime.now()
            st.session_state.exam_end_time = st.session_state.exam_start_time + timedelta(minutes=SPECIAL_TEST_MINS)

    if is_special and not st.session_state.session_done:
        time_left = st.session_state.exam_end_time - datetime.now()
        if time_left.total_seconds() <= 0:
            st.error("⏱️ TIME IS UP! The exam has officially ended.")
            save_session(username, cid, st.session_state.score, target_qs, st.session_state.session_qs)
            st.session_state.session_done = True
            time.sleep(2)
            st.rerun()

    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Abandon"):
            reset_quiz()
            st.session_state.page = "home"
            st.rerun()
    with col_title:
        title_suffix = " (SPECIAL TIMED EXAM)" if is_special else ""
        st.markdown(f"### {chapter['emoji']} {chapter['title']}{title_suffix}")
        
        if is_special and not st.session_state.session_done:
            end_str = st.session_state.exam_end_time.strftime("%I:%M %p")
            st.markdown(f"<div style='color:#d4a843; font-weight:bold;'>⚠️ Exam strictly ends at {end_str}</div>", unsafe_allow_html=True)

    if st.session_state.session_done:
        final_score = st.session_state.score
        pct = round((final_score / target_qs) * 100)
        st.markdown("---")
        st.markdown(f'<div class="stat-box"><div class="stat-val">{final_score}/{target_qs}</div><div class="stat-label">Chapter {cid} Complete — {pct}%</div></div>', unsafe_allow_html=True)
        st.markdown("")
        if pct >= 80: st.success("🎯 Outstanding performance. You are ready for the real exam.")
        elif pct >= 60: st.warning("Good effort. Review your missed answers below.")
        else: st.error("Needs more revision on this chapter.")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔄 Retry"):
                st.session_state.q_num = 1
                reset_quiz()
                st.session_state.quiz_chapter = cid
                st.session_state.is_special_test = is_special
                st.session_state.page = "quiz"
                st.rerun()
        with c2:
            if st.button("📚 All Chapters"):
                reset_quiz()
                st.session_state.page = "home"
                st.rerun()
        with c3:
            if st.button("📊 History"):
                reset_quiz()
                st.session_state.page = "history"
                st.rerun()
        return

    q_num = st.session_state.q_num
    score = st.session_state.score
    st.progress(((q_num - 1) / target_qs))

    if st.session_state.current_q is None:
        pk = preload_key(cid, q_num)
        preloaded = st.session_state.get(pk)
        if preloaded:
            st.session_state.current_q = preloaded
            del st.session_state[pk]
            st.session_state.selected = None
            st.session_state.answered = False
        else:
            with st.spinner("Generating NISM-standard question..."):
                prev_topics = [q["topic"] for q in st.session_state.session_qs]
                q_data = generate_question(chapter, prev_topics, is_special)
                if q_data is None:
                    return
                st.session_state.current_q = q_data
                st.session_state.selected = None
                st.session_state.answered = False

    q = st.session_state.current_q

    if q_num < target_qs:
        next_pk = preload_key(cid, q_num + 1)
        prev_topics = [sq["topic"] for sq in st.session_state.session_qs] + [q["topic"]]
        start_preload(chapter, prev_topics, next_pk, is_special)

    st.markdown(f"""
    <div class="question-box">
        <div class="q-label">Question {q_num} of {target_qs}</div>
        <div class="q-text">{q['question']}</div>
    </div>
    """, unsafe_allow_html=True)

    option_labels = [f"{chr(65+i)}. {opt}" for i, opt in enumerate(q["options"])]

    if not st.session_state.answered:
        selected_label = st.radio("Choose your answer:", option_labels, key=f"radio_{q_num}", label_visibility="collapsed")
        selected_idx = option_labels.index(selected_label) if selected_label else 0

        if st.button("Submit Answer →"):
            st.session_state.selected = selected_idx
            st.session_state.answered = True
            if selected_idx == q["correctIndex"]:
                st.session_state.score += 1
            st.session_state.session_qs.append({
                "question": q["question"],
                "options": q["options"],
                "correctIndex": q["correctIndex"],
                "selectedIndex": selected_idx,
                "explanation": q["explanation"],
                "topic": q["topic"]
            })
            st.rerun()
    else:
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

        cls = "correct" if is_correct else "wrong"
        label = "✓ Correct!" if is_correct else "✗ Incorrect"
        st.markdown(f"""
        <div class="explanation-box {cls}">
            <div class="exp-label {cls}">{label}</div>
            <div class="exp-text">{q['explanation']}</div>
        </div>
        """, unsafe_allow_html=True)

        btn_label = "See Results →" if q_num >= target_qs else "Next Question →"
        
        if st.button(btn_label):
            if q_num < target_qs:
                st.session_state.q_num += 1
                st.session_state.current_q = None
                st.rerun()
            else:
                save_session(username, cid, st.session_state.score, target_qs, st.session_state.session_qs)
                st.session_state.session_done = True
                st.rerun()

def page_notes():
    st.markdown("## 📝 Live Study Notes Generator")
    st.markdown("*Use Gemini to deeply analyze textbook chapters into highly-detailed, exam-ready study material.*")
    st.markdown("---")

    chapter_options = [f"Chapter {c['id']} — {c['title']}" for c in CHAPTERS]
    selected_ch_str = st.selectbox("Select Chapter to Summarize:", chapter_options)
    ch_id = int(selected_ch_str.split("—")[0].replace("Chapter", "").strip())
    chapter = get_chapter_by_id(ch_id)

    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("✨ Generate Live Notes", use_container_width=True):
            with st.spinner(f"Writing comprehensive chapter material..."):
                notes_text = generate_chapter_notes(chapter)
                
                if notes_text:
                    st.session_state.current_notes = notes_text
                    st.session_state.notes_chapter_id = ch_id
                    st.session_state.notes_pdf_bytes = create_pdf_bytes(notes_text)
                    st.rerun()
            
    if "current_notes" in st.session_state and "notes_pdf_bytes" in st.session_state:
        with col2:
            date_str = datetime.now().strftime("%Y%m%d")
            fname = f"NISM_Academy_Study_Notes_Ch{st.session_state.notes_chapter_id}_{date_str}.pdf"
            
            st.download_button(
                label="📄 Download Backup PDF", 
                data=st.session_state.notes_pdf_bytes, 
                file_name=fname, 
                mime="application/pdf",
                use_container_width=True
            )
        
        st.markdown("---")
        st.markdown(f"### Live Material: {chapter['title']}")
        st.markdown(f"""
        <div style="background-color: #1a1d24; border: 1px solid #2a2d35; border-radius: 8px; padding: 25px; color: #f0e8d8;">
            {st.session_state.current_notes}
        </div>
        """, unsafe_allow_html=True)

def page_history():
    st.markdown("## 📊 Exam History")
    st.markdown("---")
    
    if st.button("← Back to Chapters"):
        st.session_state.page = "home"
        st.rerun()

    username = st.session_state.username
    sessions = get_all_sessions(username)
    
    if not sessions:
        st.info("No exam sessions saved yet for this profile.")
        return

    for sess in sessions:
        try:
            sid, ch_id, score, total, date = sess
            chapter = get_chapter_by_id(ch_id)
            pct = round((score / total) * 100) if total else 0
            icon = pct_color(pct)
            
            ch_name = f"Chapter {ch_id} (SPECIAL EXAM)" if total == 30 else f"Chapter {ch_id}"

            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                **{icon} {ch_name}** &nbsp;·&nbsp;
                <span style="color:#d4a843;font-family:'DM Mono',monospace;font-size:13px">{score}/{total} ({pct}%)</span> &nbsp;·&nbsp;
                <span style="color:#5a5a6a;font-family:'DM Mono',monospace;font-size:11px">{date}</span>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("Review", key=f"review_{sid}"):
                    st.session_state.review_session_id = sid
                    st.session_state.page = "review"
                    st.rerun()

            st.markdown('<hr style="margin:8px 0;border-color:#1a1d24">', unsafe_allow_html=True)
        except Exception:
            continue

def page_review():
    sid = st.session_state.get("review_session_id")
    if not sid:
        st.session_state.page = "history"
        st.rerun()

    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("SELECT chapter, score, total, date FROM sessions WHERE id=?", (sid,))
        sess = cur.fetchone()
        con.close()
    except Exception:
        st.session_state.page = "history"
        st.rerun()
        return

    if not sess:
        st.session_state.page = "history"
        st.rerun()
        return

    ch_id, score, total, date = sess
    chapter = get_chapter_by_id(ch_id)
    pct = round((score / total) * 100) if total else 0

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("← Back to History"):
            st.session_state.page = "history"
            st.rerun()
            
    with col2:
        username = st.session_state.username
        pdf_bytes = build_exam_pdf_content(sid, username)
        if pdf_bytes:
            fname = f"NISM_QuizScorecard_{username}_Ch{ch_id}_{date.replace(' ','_').replace(',','').replace(':','')}.pdf"
            st.download_button(label="📄 Download Exam PDF", data=pdf_bytes, file_name=fname, mime="application/pdf")
        else:
            st.error("Missing FPDF Engine.")

    st.markdown(f"## 🔖 Review — {chapter['emoji']} {chapter['title']}")
    st.markdown(f'<p style="font-family:\'DM Mono\',monospace;font-size:12px;color:#5a5a6a">{date} &nbsp;·&nbsp; Score: {score}/{total} ({pct}%) &nbsp;·&nbsp; {pct_color(pct)}</p>', unsafe_allow_html=True)
    st.markdown("---")

    rows = get_session_questions(sid)
    if not rows:
        st.warning("No questions found for this session.")
        return

    for i, row in enumerate(rows, 1):
        try:
            question, options_json, correct_idx, selected_idx, explanation, topic, is_correct = row
            options = json.loads(options_json)
            cls = "correct" if is_correct else "wrong"

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
        except Exception:
            continue

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        if "username" in st.session_state:
            st.markdown(f"👤 **Profile:** {st.session_state.username}")
            if st.button("Logout", key="logout_btn"):
                del st.session_state["username"]
                st.session_state.page = "login"
                st.rerun()
            st.markdown("---")

        st.markdown("### Settings")
        api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.get("api_key", ""),
            type="password"
        )
        st.session_state.api_key = api_key

        st.markdown("---")
        model_labels = [m["label"] for m in GEMINI_MODELS]
        current_id = st.session_state.get("selected_model", GEMINI_MODELS[0]["id"])
        current_idx = next((i for i, m in enumerate(GEMINI_MODELS) if m["id"] == current_id), 0)
        chosen = st.selectbox("Gemini Model", model_labels, index=current_idx)
        st.session_state.selected_model = next(m["id"] for m in GEMINI_MODELS if m["label"] == chosen)

        if "username" in st.session_state:
            st.markdown("---")
            if st.button("🏠 Home", use_container_width=True):
                reset_quiz()
                st.session_state.page = "home"
                st.rerun()

            if st.button("📝 Live Study Notes", use_container_width=True):
                reset_quiz()
                st.session_state.page = "notes"
                st.rerun()

            if st.button("📊 History", use_container_width=True):
                reset_quiz()
                st.session_state.page = "history"
                st.rerun()

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Crimson Pro', Georgia, serif; }
    .stApp { background-color: #0d0f14; }
    h1, h2, h3 { color: #f0e8d8 !important; font-family: 'Crimson Pro', serif !important; }
    .chapter-card { background: #1a1d24; border: 1px solid #2a2d35; border-radius: 8px; padding: 16px 20px; margin-bottom: 10px; }
    .ch-title { font-size: 16px; font-weight: 700; color: #e0d8c8; margin-top: 2px; }
    .question-box { background: #1a1d24; border: 1px solid #2a2d35; border-radius: 8px; padding: 24px 28px; margin-bottom: 20px; }
    .q-text { font-size: 20px; font-weight: 700; color: #f0e8d8; line-height: 1.55; }
    .explanation-box { border-radius: 6px; padding: 16px 20px; margin-top: 16px; margin-bottom: 10px; border-left: 3px solid; }
    .explanation-box.correct { background: #151c19; border-color: #4a9a5a; }
    .explanation-box.wrong { background: #1c1515; border-color: #9a3a3a; }
    .exp-text { font-size: 15px; color: #b8b0a0; line-height: 1.65; }
    .stButton > button { background: #1a1d24 !important; border: 1px solid #d4a843 !important; color: #d4a843 !important; border-radius: 5px !important; }
    .stButton > button:hover { background: #d4a843 !important; color: #0d0f14 !important; }
    .review-q { background: #1a1d24; border: 1px solid #2a2d35; border-radius: 8px; padding: 20px 24px; margin-bottom: 14px; }
    .review-q.correct { border-left: 4px solid #4a9a5a; }
    .review-q.wrong { border-left: 4px solid #9a3a3a; }
    .option-line { padding: 6px 0; font-size: 15px; color: #b8b0a0; }
    .option-line.correct-ans { color: #6aba7a; font-weight: 600; }
    .option-line.wrong-ans { color: #ca6a6a; text-decoration: line-through; }
    div[data-testid="InputInstructions"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    st.set_page_config(page_title="NISM Mock Quiz & Notes", page_icon="📘", layout="wide")
    init_db()
    inject_css()

    if "api_key" not in st.session_state:
        st.session_state.api_key = os.environ.get("GEMINI_API_KEY", "")

    if "username" not in st.session_state:
        st.session_state.page = "login"

    sidebar()

    if st.session_state.page == "login":
        page_login()
    elif st.session_state.page == "home":
        page_home()
    elif st.session_state.page == "quiz":
        page_quiz()
    elif st.session_state.page == "history":
        page_history()
    elif st.session_state.page == "review":
        page_review()
    elif st.session_state.page == "notes":
        page_notes()

if __name__ == "__main__":
    main()
