import streamlit as st
import google.generativeai as genai
import json
from fpdf import FPDF

# --- 1. PAGE CONFIG & MOBILE BRANDING ---
st.set_page_config(
    page_title="NISM PREP PORTAL",
    page_icon="🎓",
    layout="wide"
)

# Professional UI Styling
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 10px 10px 0px 0px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INITIALIZE AI ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. SESSION STATE ---
if "quiz_data" not in st.session_state: st.session_state.quiz_data = None
if "exam_data" not in st.session_state: st.session_state.exam_data = None
if "live_notes" not in st.session_state: st.session_state.live_notes = None
if "pdf_bytes" not in st.session_state: st.session_state.pdf_bytes = None

# --- 4. DATA & SYLLABUS ---
full_chapters_va = [
    "Chapter 1: Investment Landscape",
    "Chapter 2: Concept and Role of a Mutual Fund",
    "Chapter 3: Legal Structure of Mutual Funds in India",
    "Chapter 4: Legal and Regulatory Framework",
    "Chapter 5: Scheme Related Information Documents",
    "Chapter 6: Fund Administration and Services",
    "Chapter 7: Net Asset Value, Total Expense Ratio and Pricing of Units",
    "Chapter 8: Taxation, Adverse Selection and Prevention of Money Laundering",
    "Chapter 9: Mutual Fund Products",
    "Chapter 10: Investment Management",
    "Chapter 11: Helping Investors with Financial Planning",
    "Chapter 12: Helping Investors with Mutual Funds",
    "Chapter 13: Recommending Suitable Schemes to Investors"
]

# --- 5. HELPER FUNCTIONS ---

def generate_nism_notes(exam, chapter):
    prompt = f"Expertly write NISM {exam} study notes for {chapter}. Use Markdown, clear headings, and bold key terms. Keep it exam-focused."
    return model.generate_content(prompt).text

def create_pdf_bytes(text_content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_font("helvetica", size=12)
    # Filter for PDF-safe characters
    safe_text = text_content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=safe_text)
    return bytes(pdf.output())

def generate_quiz(exam, topic, num):
    prompt = f"Generate {num} MCQs for {exam} on {topic} in RAW JSON format. Keys: question, options (list), answer (string), explanation."
    res = model.generate_content(prompt)
    try:
        return json.loads(res.text.replace("```json", "").replace("```", "").strip())
    except: return None

# --- 6. MAIN APP INTERFACE ---

st.title("🎓 NISM PREP PORTAL")

# MOBILE FRIENDLY NAVIGATION (TABS INSTEAD OF SIDEBAR)
tab1, tab2, tab3 = st.tabs(["📖 Study Notes", "📝 Chapter Quiz", "🏆 Full Exam"])

# --- TAB 1: STUDY NOTES & PDF ---
with tab1:
    st.subheader("Interactive Study Material")
    chapter_choice = st.selectbox("Pick a Chapter to Study:", full_chapters_va, key="note_select")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🚀 Generate Notes", use_container_width=True):
            with st.spinner("AI writing..."):
                st.session_state.live_notes = generate_nism_notes("Series V-A", chapter_choice)
                st.session_state.pdf_bytes = None # Reset PDF until requested
    
    with col2:
        if st.session_state.live_notes:
            if st.button("📄 Prepare PDF Download", use_container_width=True):
                with st.spinner("Converting to PDF..."):
                    st.session_state.pdf_bytes = create_pdf_bytes(st.session_state.live_notes)

    if st.session_state.pdf_bytes:
        st.download_button("📥 Click to Download PDF", st.session_state.pdf_bytes, f"{chapter_choice}.pdf", "application/pdf", use_container_width=True)

    if st.session_state.live_notes:
        st.divider()
        st.markdown(st.session_state.live_notes)

# --- TAB 2: CHAPTER QUIZ ---
with tab2:
    st.subheader("10-Question Practice")
    quiz_chapter = st.selectbox("Select Chapter for Quiz:", full_chapters_va, key="quiz_select")
    
    if st.button("Generate Quiz", use_container_width=True):
        with st.spinner("Compiling questions..."):
            st.session_state.quiz_data = generate_quiz("Series V-A", quiz_chapter, 10)
    
    if st.session_state.quiz_data:
        with st.form("quiz_form"):
            user_ans = {}
            for i, q in enumerate(st.session_state.quiz_data):
                st.write(f"**Q{i+1}: {q['question']}**")
                user_ans[i] = st.radio("Options", q['options'], key=f"q{i}", label_visibility="collapsed")
            if st.form_submit_button("Submit Quiz"):
                score = sum([1 for i, q in enumerate(st.session_state.quiz_data) if user_ans[i] == q['answer']])
                st.metric("Your Score", f"{score}/10")
                for i, q in enumerate(st.session_state.quiz_data):
                    if user_ans[i] == q['answer']: st.success(f"Q{i+1} Correct: {q['explanation']}")
                    else: st.error(f"Q{i+1} Wrong. Correct: {q['answer']}. {q['explanation']}")

# --- TAB 3: FULL EXAM ---
with tab3:
    st.subheader("30-Mark Final Simulation")
    if st.button("Begin Final Exam", use_container_width=True):
        with st.spinner("Generating unique 30-mark exam..."):
            st.session_state.exam_data = generate_quiz("Series V-A", "Full Syllabus", 30)
    
    if st.session_state.exam_data:
        with st.form("exam_form"):
            user_ex = {}
            for i, q in enumerate(st.session_state.exam_data):
                st.write(f"**Q{i+1}: {q['question']}**")
                user_ex[i] = st.radio("Options", q['options'], key=f"ex{i}", label_visibility="collapsed")
            if st.form_submit_button("Submit Exam"):
                ex_score = sum([1 for i, q in enumerate(st.session_state.exam_data) if user_ex[i] == q['answer']])
                st.metric("Final Score", f"{ex_score}/30")
                if ex_score >= 15: st.success("Pass! Ready for SEBI.")
                else: st.warning("Fail. Keep studying.")
