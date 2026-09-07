"""Builds the professional technical report as a PDF.

One-off build script. Run with:
    python docs/report/build_report.py
Produces docs/report/UrduStack_Technical_Report.pdf

Every metric, count, and claim below is drawn only from artifacts already
committed in this repository (tests/eval_metrics_full_t0.4.json,
tests/adversarial_results_model.csv, tests/novel_probe_results.csv,
PROJECT_SUMMARY.md, README.md) — nothing here is invented for the report.
"""

import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, PageBreak,
    Paragraph, Spacer, Image, Table, TableStyle, ListFlowable, ListItem,
    KeepTogether, FrameBreak, CondPageBreak
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas as canvas_mod
from reportlab.pdfbase.pdfmetrics import stringWidth

ROOT = Path(__file__).resolve().parent.parent.parent
DIAG = ROOT / "docs" / "diagrams"
SHOT = ROOT / "docs" / "screenshots"
OUT = ROOT / "docs" / "report" / "UrduStack_Technical_Report.pdf"

# ---------------- palette ----------------
INK = colors.HexColor("#111827")
SUBTLE = colors.HexColor("#4b5563")
TEAL = colors.HexColor("#0f766e")
TEAL_DARK = colors.HexColor("#134e4a")
RULE = colors.HexColor("#d1d5db")
LIGHT = colors.HexColor("#f3f4f6")
RED = colors.HexColor("#b91c1c")
AMBER = colors.HexColor("#92400e")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=20, leading=24,
                           spaceBefore=18, spaceAfter=10, textColor=TEAL_DARK, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=15, leading=19,
                           spaceBefore=14, spaceAfter=7, textColor=TEAL_DARK, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("H3", parent=styles["Heading3"], fontSize=12.5, leading=16,
                           spaceBefore=10, spaceAfter=5, textColor=INK, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10.3, leading=15,
                           spaceAfter=8, textColor=INK, alignment=TA_JUSTIFY, fontName="Helvetica"))
styles.add(ParagraphStyle("BodyLeft", parent=styles["Body"], alignment=TA_LEFT))
styles.add(ParagraphStyle("Small", parent=styles["Body"], fontSize=8.7, leading=11.5, textColor=SUBTLE))
styles.add(ParagraphStyle("Caption", parent=styles["Body"], fontSize=9, leading=12,
                           textColor=SUBTLE, alignment=TA_CENTER, spaceBefore=4, spaceAfter=14, fontName="Helvetica-Oblique"))
styles.add(ParagraphStyle("Quote", parent=styles["Body"], fontSize=9.7, leading=13.5,
                           leftIndent=16, textColor=SUBTLE, fontName="Courier", backColor=LIGHT))
styles.add(ParagraphStyle("TitlePage", parent=styles["Title"], fontSize=32, leading=38, textColor=INK))
styles.add(ParagraphStyle("SubtitlePage", parent=styles["Normal"], fontSize=15, leading=20,
                           alignment=TA_CENTER, textColor=TEAL, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("TOCHeading1", parent=styles["Normal"], fontSize=11.5, leading=16,
                           textColor=INK, fontName="Helvetica-Bold", spaceBefore=4))
styles.add(ParagraphStyle("TOCHeading2", parent=styles["Normal"], fontSize=10, leading=13,
                           leftIndent=14, textColor=SUBTLE, fontName="Helvetica"))

fig_counter = [0]
tbl_counter = [0]
figures_list = []
tables_list = []


def figure(path, caption, width=15.5 * cm):
    fig_counter[0] += 1
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        iw, ih = im.size
    h = width * ih / iw
    max_h = 20 * cm
    if h > max_h:
        h = max_h
        width = max_h * iw / ih
    cap = f"Figure {fig_counter[0]}. {caption}"
    figures_list.append(cap)
    return [Image(str(path), width=width, height=h), Paragraph(cap, styles["Caption"])]


def table_caption(text_):
    tbl_counter[0] += 1
    cap = f"Table {tbl_counter[0]}. {text_}"
    tables_list.append(cap)
    return Paragraph(cap, styles["Caption"])


def styled_table(data, col_widths=None, header=True, font_size=9.2):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(style))
    return t


def h1(text_, bm):
    p = Paragraph(text_, styles["H1"])
    p._bookmarkName = bm
    return p


def h2(text_, bm):
    p = Paragraph(text_, styles["H2"])
    p._bookmarkName = bm
    return p


def h3(text_):
    return Paragraph(text_, styles["H3"])


def body(text_):
    return Paragraph(text_, styles["Body"])


# ---------------- doc template with header/footer + TOC bookmarking ----------------

class ReportDoc(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style = flowable.style.name
            text_ = flowable.getPlainText()
            bm = getattr(flowable, "_bookmarkName", None)
            if style == "H1":
                key = bm or text_
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text_, key, level=0, closed=False)
                self.notify("TOCEntry", (0, text_, self.page, key))
            elif style == "H2":
                key = bm or text_
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text_, key, level=1, closed=False)
                self.notify("TOCEntry", (1, text_, self.page, key))


def header_footer(canv: canvas_mod.Canvas, doc):
    canv.saveState()
    w, h_ = A4
    if doc.page > 1:
        canv.setStrokeColor(RULE)
        canv.setLineWidth(0.6)
        canv.line(2 * cm, h_ - 1.55 * cm, w - 2 * cm, h_ - 1.55 * cm)
        canv.setFont("Helvetica", 8.3)
        canv.setFillColor(SUBTLE)
        canv.drawString(2 * cm, h_ - 1.4 * cm, "UrduStack — Technical Report")
        canv.drawRightString(w - 2 * cm, h_ - 1.4 * cm, "Code-switch-aware Urdu NLP infrastructure")

        canv.line(2 * cm, 1.55 * cm, w - 2 * cm, 1.55 * cm)
        canv.setFont("Helvetica", 8.3)
        canv.drawString(2 * cm, 1.15 * cm, "Shahoud Shahid · Munaza Tariq")
        canv.drawRightString(w - 2 * cm, 1.15 * cm, f"Page {doc.page - 1}")
    canv.restoreState()


doc = ReportDoc(str(OUT), pagesize=A4,
                 leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2.1 * cm, bottomMargin=2 * cm,
                 title="UrduStack Technical Report", author="Shahoud Shahid, Munaza Tariq")

frame_title = Frame(2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4 * cm, id="title")
frame_body = Frame(2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4.3 * cm, id="body")

doc.addPageTemplates([
    PageTemplate(id="Title", frames=[frame_title], onPage=lambda c, d: None),
    PageTemplate(id="Body", frames=[frame_body], onPage=header_footer),
])

story = []

# ============================================================= TITLE PAGE
story.append(Spacer(1, 3.4 * cm))
rule_tbl = Table([[""]], colWidths=[2.2 * cm], rowHeights=[0.1 * cm])
rule_tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TEAL)]))
rule_tbl.hAlign = "CENTER"
story.append(rule_tbl)
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph("UrduStack", styles["TitlePage"]).__class__(
    "UrduStack", ParagraphStyle("TT", parent=styles["TitlePage"], alignment=TA_CENTER)))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph("A Code-Switch-Aware Urdu NLP Infrastructure for<br/>Scam and Harassment Detection",
                        ParagraphStyle("subT", parent=styles["SubtitlePage"], fontSize=16)))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph("Technical Report", ParagraphStyle("techrep", parent=styles["Normal"],
             fontSize=13, alignment=TA_CENTER, textColor=SUBTLE)))
story.append(Spacer(1, 2.6 * cm))

tbl = Table([
    ["Authors", "Shahoud Shahid, Munaza Tariq"],
    ["Repository", "github.com/munazat/UrduStack"],
    ["Date", "September 2026"],
    ["Deployment", "Hugging Face Spaces / Google Colab (T4 GPU)"],
], colWidths=[4.5 * cm, 9.5 * cm])
tbl.setStyle(TableStyle([
    ("FONTSIZE", (0, 0), (-1, -1), 11),
    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
    ("TEXTCOLOR", (0, 0), (0, -1), TEAL_DARK),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
]))
story.append(tbl)

story.append(NextPageTemplate("Body"))
story.append(PageBreak())

# ============================================================= ABSTRACT
story.append(h1("Abstract", "abstract"))
story.append(body(
    "Pakistani digital text routinely mixes Urdu script, Roman Urdu, and English within a single "
    "sentence, which lets scam and harassment content slip past moderation tools built for a single "
    "script. UrduStack is a self-hosted NLP pipeline that first normalizes code-switched text into "
    "Urdu script and then classifies it for scam and toxic content using a LoRA-fine-tuned "
    "XLM-RoBERTa model combined with a hardened heuristic layer in a max-ensemble. The system reaches "
    "89.7% accuracy and an F1 score of 87.1% on a 107-example held-out test set, and passes 12 of 12 "
    "adversarial red-team cases against the deployed model — a result independently driven by the "
    "trained model on 8 of those 12 cases, not the keyword layer alone. On a separate probe of 11 "
    "phrases matching none of the heuristic's known patterns, the trained model correctly generalized "
    "on 7, demonstrating genuine semantic understanding rather than memorized keyword matching. The "
    "system additionally performs named-entity recognition, Urdu speech-to-text transcription, and "
    "plain-language explanation, and is reachable through a website, a Gradio demo, and a WhatsApp "
    "bot — all backed by the same scoring logic. This report documents the system's architecture, "
    "methodology, implementation, evaluation, and — deliberately, in equal detail — its known, "
    "currently open limitations."
))
story.append(PageBreak())

# ============================================================= ACKNOWLEDGEMENTS
story.append(h1("Acknowledgements", "ack"))
story.append(body(
    "We thank the organizers of this hackathon for the opportunity and the tight, motivating deadline. "
    "This project builds on open datasets and open-source software without which it would not exist: "
    "the Roman-Urdu-Parl parallel corpus and the Roman-Urdu-Toxic-Corpus (PURUTT) from the Hugging Face "
    "Hub community, the XLM-RoBERTa base model from Facebook AI, the PEFT/LoRA implementation from "
    "Hugging Face, OpenAI's Whisper speech-recognition model, and the FastAPI, Gradio, and PyTorch "
    "open-source projects."
))
story.append(PageBreak())

# ============================================================= TOC
story.append(h1("Table of Contents", "toc"))
toc = TableOfContents()
toc.levelStyles = [styles["TOCHeading1"], styles["TOCHeading2"]]
story.append(toc)
story.append(PageBreak())

# ============================================================= LIST OF FIGURES / TABLES (placeholder, filled at 2nd pass by reportlab's mechanism is manual here)
lof_placeholder_index = len(story)
story.append(h1("List of Figures", "lof"))
story.append(Paragraph("(See figures throughout the report; index below is generated from this build.)", styles["Small"]))
story.append(PageBreak())

lot_placeholder_index = len(story)
story.append(h1("List of Tables", "lot"))
story.append(Paragraph("(See tables throughout the report; index below is generated from this build.)", styles["Small"]))
story.append(PageBreak())

# ============================================================= 1. INTRODUCTION
story.append(h1("1. Introduction", "intro"))
story.append(body(
    "UrduStack is a unified natural-language-processing pipeline purpose-built for the way people in "
    "Pakistan actually write online: a fluid mix of Urdu script, Roman Urdu (Urdu transliterated into "
    "Latin letters), and English, often within a single sentence. It was built as a two-day hackathon "
    "MVP and has since been iteratively hardened, tested against its own claims, and re-verified "
    "against a real trained model rather than left as an untested prototype."
))
story.append(body(
    "The system's core contribution is not a single novel algorithm but a working, evaluated pipeline: "
    "normalization that survives code-switching, a risk classifier that combines a fine-tuned "
    "transformer with a fast heuristic layer, entity recognition, speech-to-text, and plain-language "
    "explanation — wired together behind one API and reachable from three different real-world "
    "surfaces."
))

story.append(h2("1.1 Report Structure", None))
story.append(body(
    "Sections 2–5 establish the problem, its real-world stakes, and the project's objectives. "
    "Sections 6–10 describe the proposed solution, its architecture, methodology, and detailed design. "
    "Sections 11–15 cover implementation specifics: the models, the pipelines, the API surface, and "
    "the user-facing interfaces. Sections 16–18 present the experimental setup, testing methodology, "
    "and results — including cases where the system currently falls short, reported with the same rigor "
    "as its successes. Sections 19–21 close with limitations, future work, and conclusions."
))
story.append(PageBreak())

# ============================================================= 2. PROBLEM STATEMENT
story.append(h1("2. Problem Statement", "problem"))
story.append(body(
    "Existing content-moderation and scam-detection tools are largely built and evaluated on English "
    "or single-script text. Pakistani digital communication routinely violates that assumption. A "
    "single scam job posting observed during this project's development reads, verbatim:"
))
story.append(Paragraph(
    '"Urgent hiring! 50000 per week, send processing fee to register."',
    styles["Quote"]))
story.append(body(
    "This sentence is entirely in Roman Urdu and English — no Urdu script appears at all — yet it "
    "carries a scam pattern (an advance-fee request tied to a job offer) that a Pakistani reader "
    "recognizes instantly. A naive English keyword filter for \"processing fee\" catches the "
    "unobfuscated case, but the same filter is defeated by trivial evasions: leetspeak "
    "(\"pr0c3ss1ng f33\"), character spacing (\"p r o c e s s i n g   f e e\"), or simple misspellings "
    "(\"procesing fee\")."
))
story.append(body(
    "Two concrete harms motivate this project. First, fake job postings circulated on Facebook, "
    "WhatsApp, and OLX target Pakistani students and jobseekers, extracting advance \"processing fees\" "
    "for positions that do not exist. Second, harassing and abusive content in the same mixed script "
    "is similarly under-served by moderation tools tuned for a single language or script."
))
story.append(PageBreak())

# ============================================================= 3. MOTIVATION
story.append(h1("3. Motivation", "motivation"))
story.append(body(
    "Three considerations shaped this project's direction beyond the problem statement itself:"
))
story.append(ListFlowable([
    ListItem(body("<b>Explainability matters as much as accuracy.</b> A risk score with no explanation "
                   "is not actionable for a non-technical user; the system needed to show which phrases "
                   "drove a verdict and why, not just output a number.")),
    ListItem(body("<b>Self-hosting is a real privacy requirement, not a preference.</b> Harassment "
                   "reports and scam complaints are sensitive; routing them through a third-party API "
                   "is a meaningfully different privacy posture than running a model on-device.")),
    ListItem(body("<b>A keyword list alone was known, going in, to be insufficient.</b> The project "
                   "deliberately invested in fine-tuning a transformer model rather than shipping a "
                   "heuristic-only detector, and — as Section 18 documents — verified that investment "
                   "actually paid off, rather than assuming it did.")),
], bulletType="bullet", leftIndent=14))
story.append(PageBreak())

# ============================================================= 4. OBJECTIVES
story.append(h1("4. Objectives", "objectives"))
story.append(body("The project set out to build and evaluate a system that:"))
objectives = [
    "Normalizes code-switched Roman Urdu / Urdu script / English text into a consistent Urdu-script representation.",
    "Classifies text as toxic/scam or clean using a model trained specifically for this data distribution, not a general-purpose LLM prompt.",
    "Explains its verdicts — which phrases contributed, and by how much.",
    "Categorizes detected threats into actionable types (fake job posting, phishing, harassment) with type-specific advice.",
    "Extracts named entities to add context to a verdict, without letting an unreliable signal silently weaken a safety message.",
    "Reaches users through more than one interface: a website, an interactive demo, and a messaging-platform bot.",
    "Is evaluated honestly — every claimed metric backed by a committed, reproducible artifact, including where the system currently fails.",
]
story.append(ListFlowable([ListItem(body(o)) for o in objectives], bulletType="1", leftIndent=14))
story.append(PageBreak())

# ============================================================= 5. BACKGROUND
story.append(h1("5. Background and Existing Approaches", "background"))
story.append(h2("5.1 English-Centric Moderation Tools", None))
story.append(body(
    "General-purpose content moderation APIs and keyword-filter systems are typically trained and "
    "tuned on English text. Applied directly to Roman Urdu or code-switched input, they miss both "
    "vocabulary (Roman-Urdu scam and abuse terms are not English words) and context (code-switching "
    "patterns differ from monolingual text)."
))
story.append(h2("5.2 General-Purpose Large Language Models", None))
story.append(body(
    "A frontier LLM API (e.g. GPT-4o) prompted directly could plausibly classify some of the same "
    "text. UrduStack differs from that approach on four structural dimensions rather than by claiming "
    "categorically better accuracy: it runs entirely on-device (no data leaves the deployment), costs "
    "$0 per request rather than a per-token API fee, responds in sub-second time versus 1–3 seconds "
    "for a typical hosted LLM call, and works fully offline. This report does not claim a measured "
    "accuracy advantage over a frontier LLM on this specific task — that head-to-head comparison has "
    "not been run — and states that limitation plainly rather than asserting an unverified win."
))
story.append(h2("5.3 Urdu-Specific NLP Models", None))
story.append(body(
    "Pretrained Urdu-script models exist (e.g. Urdu BERT variants) but generally assume Urdu-script "
    "input; they do not natively handle Roman Urdu without a normalization step first. UrduStack's "
    "architecture — normalize first, then classify — is a deliberate response to this gap, and its "
    "use of XLM-RoBERTa (a multilingual model with meaningful Roman-Urdu-adjacent pretraining data) as "
    "the classification backbone means the model handles residual Roman-Urdu tokens reasonably even "
    "when normalization is incomplete."
))
story.append(PageBreak())

# ============================================================= 6. PROPOSED SOLUTION
story.append(h1("6. Proposed Solution", "solution"))
story.append(body(
    "UrduStack is structured as a five-stage pipeline: normalize, score, extract entities, categorize "
    "the threat, and generate a plain-language, actionable recommendation. The central technical "
    "decision is a <b>max-ensemble risk scorer</b>: a LoRA-fine-tuned XLM-RoBERTa classifier and a "
    "five-pass heuristic detector are run independently, and the higher of the two scores is used. "
    "This is a deliberate defense-in-depth choice — either detector catching a threat is sufficient — "
    "verified in Section 18 to matter in practice: the trained model independently drives 8 of 12 "
    "correct scores on the project's adversarial test suite, while the heuristic layer catches "
    "obfuscation patterns (leetspeak, character spacing) that the model alone does not reliably resolve."
))
for block in figure(DIAG / "01-problem-solution.png", "Problem-to-solution overview."):
    story.append(block)
story.append(PageBreak())

# ============================================================= 7. SYSTEM ARCHITECTURE
story.append(h1("7. System Architecture", "architecture"))
story.append(body(
    "The system runs as a single FastAPI process orchestrating a set of lazily-loaded models through a "
    "central ModelManager. Four entry surfaces call into the same API: a static website, a Gradio "
    "demo, a WhatsApp bot (Flask + Twilio), and direct API clients. There is no traditional database — "
    "state is file-based: a committed static dictionary, a committed FAISS/TF-IDF phrase index, and a "
    "CSV feedback log for the active-learning loop."
))
for block in figure(DIAG / "02-system-architecture.png", "System architecture: entry surfaces, API layer, orchestration, core pipeline modules, and file-based data."):
    story.append(block)
story.append(PageBreak())

# ============================================================= 8. METHODOLOGY
story.append(h1("8. Methodology", "methodology"))
story.append(h2("8.1 Model Fine-Tuning", None))
story.append(body(
    "The risk classifier was built by fine-tuning <b>xlm-roberta-base</b> (270M parameters) with LoRA "
    "(rank 16, alpha 32, dropout 0.1, applied to the query/key/value/dense layers), producing a 4.5 MB "
    "adapter rather than a full 1.1 GB model checkpoint. Training used a class-weighted cross-entropy "
    "loss (a custom Trainer subclass) to compensate for toxic/clean class imbalance without "
    "resampling, learning rate 2e-4, batch size 16, 5 epochs, early stopping with patience 2 on "
    "validation loss, and FP16 mixed precision on a Colab T4 GPU."
))
story.append(h2("8.2 Calibration", None))
story.append(body(
    "Raw softmax outputs from fine-tuned transformers are frequently overconfident. The model's logits "
    "are scaled by a temperature T = 1.409, selected via grid search over 100 candidate values in "
    "[0.5, 5.0] against a held-out validation set, before the confidence score is reported."
))
story.append(h2("8.3 Evaluation Methodology", None))
story.append(body(
    "Three independent evaluation artifacts were produced, all against the actual trained adapter "
    "(not a heuristic stand-in), each with provenance recorded (git commit hash, timestamp, exact "
    "command): a full held-out test set evaluation, a 12-case adversarial red-team suite, and a "
    "novel-vocabulary generalization probe. Section 18 reports all three."
))
story.append(PageBreak())

# ============================================================= 9. DETAILED SYSTEM DESIGN
story.append(h1("9. Detailed System Design", "design"))
story.append(h2("9.1 Normalization Cascade", None))
story.append(body(
    "Each token is classified as Urdu-script, Roman Urdu, or other (URLs, numbers, and English pass "
    "through unchanged). Roman-Urdu tokens are resolved through a cascade: (1) a 485-word static "
    "dictionary (467 original entries plus 18 high-frequency job-posting loanwords added after "
    "testing revealed common words like \"available\" and \"processing\" were falling through to "
    "phonetic transliteration and producing unreadable output); (2) a FAISS/TF-IDF character-trigram "
    "retrieval index seeded with 587 total phrases; (3) a greedy longest-match phonetic "
    "transliterator as a last resort, guaranteeing every token produces Urdu-script output even when "
    "no dictionary or retrieval match exists."
))
story.append(h2("9.2 Risk Scoring — the Max-Ensemble", None))
for block in figure(DIAG / "04-ml-pipeline.png", "Risk scoring detail: the LoRA model and the 5-pass heuristic run independently; the ensemble takes the maximum of the two scores."):
    story.append(block)
story.append(body(
    "The heuristic branch runs five passes: (1) word-boundary phrase matching, (2) leetspeak "
    "normalization via character translation, (3) typo correction against a curated misspelling map, "
    "(4) fuzzy character-spacing detection for \"k u t t a\"-style evasion, and (5) Levenshtein "
    "edit-distance matching, which generalizes to <i>novel</i> misspellings of already-known words — "
    "not an enumerated list of specific typos."
))
story.append(h2("9.3 Threat Categorization and Recommendation", None))
story.append(body(
    "Flagged phrases are mapped to one of three threat categories — fake job posting, phishing, or "
    "harassment — each carrying a specific, actionable recommendation (e.g. harassment cases include "
    "a pointer to Pakistan's FIA Cyber Crime reporting channel). A deliberate design correction made "
    "during this project's validation: the recommendation logic no longer uses named-entity "
    "recognition to decide whether to show a \"verify the organization independently\" caution. NER "
    "was found to misclassify the Urdu word for \"job\" itself as an ORGANIZATION entity at 96% "
    "confidence, which had been silently suppressing that caution on genuine scam messages. NER "
    "output is still shown to the user for information; it no longer gates a safety-relevant message."
))
story.append(PageBreak())

# ============================================================= 10. TECHNOLOGIES AND TOOLS
story.append(h1("10. Technologies and Tools", "tech"))
story.append(table_caption("Core technology stack."))
tech_rows = [
    ["Layer", "Technology"],
    ["API framework", "FastAPI + Pydantic (request/response validation), Uvicorn"],
    ["ML framework", "PyTorch, Hugging Face Transformers, PEFT (LoRA)"],
    ["Risk model", "xlm-roberta-base + LoRA adapter"],
    ["NER model", "XLM-RoBERTa fine-tuned on WikiAnn"],
    ["Speech-to-text", "OpenAI Whisper (base)"],
    ["Retrieval", "FAISS (IndexFlatIP) + character-trigram TF-IDF"],
    ["Demo UI", "Gradio 6.x (4-tab interface)"],
    ["Distribution", "Flask + Twilio (WhatsApp), vanilla JS static site"],
    ["Report generation", "matplotlib (PDF export), reportlab (this report)"],
    ["Testing", "pytest (46 unit tests), custom adversarial/regression harnesses"],
    ["CI", "GitHub Actions"],
    ["Deployment", "Docker (python:3.11-slim) → Hugging Face Spaces, or Colab T4 GPU"],
]
story.append(styled_table(tech_rows, col_widths=[4 * cm, 10.5 * cm]))
story.append(PageBreak())

# ============================================================= 11. IMPLEMENTATION
story.append(h1("11. Implementation", "implementation"))
story.append(body(
    "The codebase is organized as a FastAPI application (<font face='Courier'>app/</font>) with "
    "clearly separated model wrappers (<font face='Courier'>app/models/</font>), utility pipelines "
    "(<font face='Courier'>app/utils/</font>), and API route definitions "
    "(<font face='Courier'>app/api/endpoints.py</font>). Training and data-preparation scripts live "
    "under <font face='Courier'>scripts/</font>, and the full test suite — unit tests, adversarial "
    "harnesses, and evaluation scripts — under <font face='Courier'>tests/</font>."
))
story.append(h2("11.1 Graceful Degradation", None))
story.append(body(
    "The risk model, NER model, and transcription model are all optional heavy dependencies at "
    "import time. If torch/transformers/peft are not installed, the FastAPI application still starts "
    "successfully and the risk scorer falls back to the heuristic-only path automatically; NER "
    "returns an empty entity list rather than raising an error. This was verified directly during "
    "this project's validation — the full application, including every API endpoint, was exercised "
    "with these dependencies absent and produced correct, non-crashing responses throughout."
))
story.append(h2("11.2 Active Learning Loop", None))
story.append(body(
    "A <font face='Courier'>/feedback</font> endpoint accepts a user's correction (was the verdict "
    "right?) and appends it to a CSV log. A separate consumer script filters low-confidence and "
    "incorrect rows, deduplicates, and produces a retraining-ready CSV. This data path is functional "
    "and tested; it is not yet wired into an automated retraining schedule, which is noted as future "
    "work in Section 20."
))
story.append(PageBreak())

# ============================================================= 12. ALGORITHMS / MODELS / PIPELINES
story.append(h1("12. Algorithms, Models, and Pipelines", "algorithms"))
for block in figure(DIAG / "03-workflow.png", "End-to-end data flow through analyze_text() — the six pipeline stages executed on every /analyze request."):
    story.append(block)
story.append(table_caption("Training configuration for the LoRA risk classifier."))
train_rows = [
    ["Parameter", "Value"],
    ["Base model", "xlm-roberta-base (270M parameters)"],
    ["LoRA rank / alpha / dropout", "16 / 32 / 0.1"],
    ["LoRA target modules", "query, key, value, dense"],
    ["Learning rate", "2e-4"],
    ["Batch size", "16"],
    ["Epochs", "5 (early stopping, patience 2)"],
    ["Training samples", "~80,000 (after deduplication)"],
    ["Precision", "FP16 (mixed precision, T4 GPU)"],
    ["Temperature (calibration)", "1.409 (grid search, 100 candidates)"],
]
story.append(styled_table(train_rows, col_widths=[6 * cm, 8.5 * cm]))
story.append(Spacer(1, 8))
story.append(table_caption("Training and evaluation datasets."))
ds_rows = [
    ["Dataset", "Rows", "Role"],
    ["Roman-Urdu-Parl (HF)", "6.37M", "Frequency map source (Tier-1 normalization; not shipped in the repo)"],
    ["Roman-Urdu-Toxic-Corpus / PURUTT", "72,700", "Primary training data — toxic vs. clean"],
    ["Roman Urdu Hate Speech (HF)", "variable", "Supplementary toxic samples"],
    ["Urdu Spam Dataset (HF)", "variable", "Supplementary spam samples"],
    ["Synthetic scam data (generated)", "1,500", "7 scam categories: job, lottery, phishing, investment, charity, shopping, loan"],
]
story.append(styled_table(ds_rows, col_widths=[5.5 * cm, 2.5 * cm, 6.5 * cm], font_size=8.7))
story.append(PageBreak())

# ============================================================= 13. API DESIGN
story.append(h1("13. API and Data Design", "api"))
story.append(body(
    "There is no traditional relational or document database in this system — a deliberate, "
    "appropriately-scoped choice for its data needs. State is file-based: a committed Python "
    "dictionary for the static lexicon, a committed JSON file for the RAG phrase index, and an "
    "append-only CSV for feedback. The API surface is a single FastAPI router with eight endpoints:"
))
api_rows = [
    ["Method", "Endpoint", "Description"],
    ["GET", "/health", "Model load status for each component"],
    ["POST", "/normalize", "Code-switch-aware Roman Urdu → Urdu normalization"],
    ["POST", "/risk-score", "Risk classification with explanation and debug scores"],
    ["POST", "/transcribe", "Urdu speech-to-text (audio upload)"],
    ["POST", "/ner", "Named entity extraction"],
    ["POST", "/simplify", "Lexical simplification to plain-language Urdu"],
    ["POST", "/analyze", "Full pipeline: normalize + risk + NER + categorize + recommend"],
    ["POST", "/feedback", "Active-learning feedback submission"],
]
story.append(styled_table(api_rows, col_widths=[1.6 * cm, 3.2 * cm, 9.2 * cm], font_size=8.9))
story.append(Spacer(1, 8))
story.append(body(
    "Every request/response schema is validated through Pydantic models (e.g. minimum text length on "
    "input, enumerated valid labels on feedback submission); this was verified directly by sending "
    "malformed requests to a live server, which correctly returned HTTP 422 with a descriptive error "
    "rather than a 500 or silently accepting invalid data. CORS middleware is enabled so that a "
    "separately-hosted frontend can call the API from a browser."
))
story.append(PageBreak())

# ============================================================= 14. UI/UX
story.append(h1("14. UI/UX Design", "uiux"))
story.append(body(
    "Three interfaces share the same backend logic, so a verdict never differs by which surface a "
    "user happens to use. The static website (Figure 6) is a single self-contained HTML page with "
    "no build step, prioritizing a fast first interaction. The Gradio playground (Figure 7) adds a "
    "phrase-contribution bar chart, a PDF export button, a speech-analysis tab, and a side-by-side "
    "comparison against a naive English-keyword baseline to make the system's added value legible. "
    "The WhatsApp bot delivers the same verdict as a formatted chat message, reaching users on the "
    "platform where scams and harassment actually circulate rather than requiring them to visit a "
    "separate tool."
))
for block in figure(DIAG / "05-user-journey.png", "User journey across the three real entry points, sharing one decision engine and an optional feedback loop."):
    story.append(block)
story.append(PageBreak())

# ============================================================= 15. FEATURES
story.append(h1("15. Features", "features"))
for block in figure(DIAG / "06-feature-overview.png", "Feature overview: the six implemented capabilities."):
    story.append(block)
story.append(PageBreak())

# ============================================================= 16. EXPERIMENTAL SETUP
story.append(h1("16. Experimental Setup", "experimental"))
story.append(body(
    "All results in Section 18 were produced by installing the project's CPU-only PyTorch, "
    "Transformers, and PEFT dependencies, loading the committed LoRA adapter from "
    "<font face='Courier'>models/risk_lora/</font>, and running the project's own evaluation scripts "
    "(<font face='Courier'>tests/run_evaluation.py</font>, "
    "<font face='Courier'>tests/run_adversarial_colab.py</font>) directly against the real model — "
    "not a mock, not the heuristic fallback, and not a stale cached result. This is a deliberate "
    "methodological point: earlier project documentation had, at various points, described metrics "
    "from an unsaved or unreproducible session; every number in this report is backed by a "
    "committed CSV or JSON file carrying a git commit hash and timestamp."
))
story.append(PageBreak())

# ============================================================= 17. TESTING AND VALIDATION
story.append(h1("17. Testing and Validation", "testing"))
story.append(h2("17.1 Unit Tests", None))
story.append(body(
    "46 pytest unit tests cover the heuristic scorer, the lexical simplifier, the text-collapse "
    "preprocessor, script detection, typo correction, risk categorization, loanword normalization, "
    "and — added after a real defect was found in this pipeline — a regression test that actually "
    "generates a PDF report and asserts it is non-trivially sized, and an AST-based check that the "
    "static dictionary contains no duplicate keys."
))
story.append(h2("17.2 End-to-End Validation", None))
story.append(body(
    "Beyond unit tests, the complete application was exercised as a running system: a live Uvicorn "
    "server was started and hit over real HTTP (not an in-process test client) for the health check "
    "and risk-scoring endpoints; the WhatsApp bot's Flask webhook was sent a real POST request and "
    "produced a correctly-formatted reply using the live trained ensemble; the Gradio playground was "
    "driven with a headless browser (Playwright), filling the input field, clicking Analyze, and "
    "capturing the rendered result, including a successful PDF download."
))
story.append(h2("17.3 Continuous Integration", None))
story.append(body(
    "A GitHub Actions workflow runs the unit test suite and a heuristic-only adversarial regression "
    "check on every push. The regression suite is explicitly split into cases the CI environment (no "
    "GPU) can verify, versus documented cases where the heuristic alone is known to differ from the "
    "real deployed model — the latter are reported, not hidden inside a passing aggregate count."
))
story.append(PageBreak())

# ============================================================= 18. RESULTS
story.append(h1("18. Results", "results"))

story.append(h2("18.1 Risk Classifier Performance", None))
story.append(table_caption("Risk classifier performance, full 107-example held-out test set, real trained adapter."))
metrics_rows = [
    ["Metric", "Score"],
    ["Accuracy", "89.7%"],
    ["Precision (toxic/scam)", "92.5%"],
    ["Recall (toxic/scam)", "82.2%"],
    ["F1 (toxic/scam)", "87.1%"],
    ["Macro precision", "90.3%"],
    ["Macro recall", "88.7%"],
    ["Macro F1", "89.3%"],
]
story.append(styled_table(metrics_rows, col_widths=[7 * cm, 4 * cm]))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "Source: tests/eval_metrics_full_t0.4.json (provenance: git commit, timestamp, and exact command "
    "recorded in the file itself).", styles["Small"]))

story.append(h2("18.2 Adversarial Red-Team Results", None))
story.append(body(
    "The original 12-case adversarial suite (leetspeak, character-spacing evasion, misspellings, "
    "mixed-script attacks, Roman-Urdu scam phrasing) passes 12 of 12 against the deployed max-ensemble. "
    "Per-case debug scores show the LoRA model independently driving 8 of the 12 correct results — "
    "for example, the baseline scam case scores 1.00 from the model alone, before any heuristic "
    "contribution is added."
))

story.append(h2("18.3 Novel-Vocabulary Generalization", None))
story.append(body(
    "To distinguish genuine semantic generalization from keyword memorization, the trained model was "
    "tested on 11 phrases matching none of the heuristic's known patterns. Table 4 reports the result "
    "in full, including the cases where the model still fails."
))
gen_rows = [
    ["Phrase (paraphrased)", "Result", "LoRA score"],
    ["A novel insult (\"gadha/nalayak\")", "Caught", "0.98"],
    ["Investment-scam pitch", "Caught", "0.99"],
    ["\"Idiot\" insult", "Caught", "0.97"],
    ["Thief accusation (\"chor\")", "Caught", "0.96"],
    ["Advance-deposit request", "Caught", "1.00"],
    ["\"Easy money\" pitch", "Caught", "0.98"],
    ["Bank-transfer instruction", "Caught", "1.00"],
    ["Roman-Urdu fee request", "MISSED", "0.04"],
    ["A direct death threat", "MISSED", "0.10"],
    ["Fee-synonym scam phrasing", "MISSED", "0.18"],
    ["Romance / gift-card scam", "MISSED", "0.01"],
]
story.append(styled_table(gen_rows, col_widths=[7.5 * cm, 2.5 * cm, 2.5 * cm], font_size=9))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "Source: tests/novel_probe_results.csv, generated 2026-09-07. The missed death threat is the "
    "single most important open finding in this report and is discussed again in Section 19.",
    styles["Small"]))

story.append(h2("18.4 Known, Currently Unfixed False Positives", None))
story.append(body(
    "Testing the live deployed ensemble (not just the heuristic) surfaced two real false positives: "
    "a legitimate university fee mention scores 0.98 (HIGH) from the model alone, and a bare string "
    "of numbers with no other words scores 1.00 (HIGH). Follow-up probes ruled out a simple "
    "\"numbers\" explanation — the single word \"salary\" alone scores 0.99, while \"12345\" alone "
    "scores 0.01 — indicating the model has learned spurious associations with specific tokens from "
    "the synthetic scam-generation templates rather than a generalizable short-text rule. This is "
    "deliberately left unpatched at the code level: a length- or keyword-based override would either "
    "reintroduce the keyword-matching approach this project moved away from, or risk suppressing "
    "genuinely correct short-text detections elsewhere (a single toxic word, correctly, scores high "
    "on its own). The documented fix is retraining with more short-text diversity in the negative "
    "class."
))

story.append(h2("18.5 UI/UX Verification", None))
for block in figure(SHOT / "04_gradio_result.png", "The Gradio playground, live, analyzing a real scam message end-to-end.", width=14.5*cm):
    story.append(block)
story.append(PageBreak())
for block in figure(SHOT / "02_static_site_result.png", "The static website, live, showing the same verdict — confirming both surfaces agree.", width=14.5*cm):
    story.append(block)
story.append(PageBreak())

# ============================================================= 19. LIMITATIONS
story.append(h1("19. Limitations", "limitations"))
limitations = [
    "<b>Missed death threat.</b> A direct death threat (\"jaan se maar doonga\") scores 0.10 — well "
    "below the high-risk threshold — even from the trained model, not just the heuristic. This is the "
    "highest-priority open issue in the project.",
    "<b>Short-input false positives.</b> The model overtriggers on some short or sparse inputs "
    "independent of any identifiable keyword pattern (Section 18.4).",
    "<b>Frequency map not shipped.</b> The Tier-1 normalization frequency map, built from 6.37M "
    "parallel sentences, is generated on Colab but not committed to the repository due to size; "
    "normalization falls back to the 485-word static dictionary and the FAISS retrieval index.",
    "<b>NER extraction quality is uneven.</b> Named-entity recognition on this pipeline's normalized, "
    "sometimes-transliterated text produces occasional misclassifications (Section 9.2); it is treated "
    "as informational rather than authoritative for exactly this reason.",
    "<b>No formal head-to-head comparison against a frontier LLM.</b> The privacy, cost, and latency "
    "advantages over an API-based LLM are structural and can be stated with confidence; a measured "
    "accuracy comparison on this specific task has not been run.",
    "<b>WhatsApp distribution is demo-time only.</b> The bot is functional and tested end-to-end, but "
    "is not currently deployed as a persistent, always-on service.",
    "<b>Multi-category scam detection covers 3 of 7 generated categories.</b> Synthetic training data "
    "spans 7 scam types; the deployed categorizer currently distinguishes job scams, phishing, and "
    "harassment.",
]
story.append(ListFlowable([ListItem(body(l)) for l in limitations], bulletType="bullet", leftIndent=14))
story.append(PageBreak())

# ============================================================= 20. FUTURE WORK
story.append(h1("20. Future Work", "future"))
future = [
    "Retrain the risk classifier with expanded negative-class short-text examples and additional "
    "threat/harassment vocabulary to close the death-threat and short-input-false-positive gaps "
    "documented in Section 18.",
    "Commit the full Tier-1 frequency map, or explicitly document Tier-1 normalization as a "
    "Colab-only build step until it is shipped.",
    "Deploy the WhatsApp bot as a persistent service rather than a demo-time Colab tunnel.",
    "Extend multi-category threat detection to the remaining synthetic scam categories (lottery, "
    "charity, investment, loan).",
    "Run a formal, reproducible head-to-head evaluation against a frontier LLM API on the project's "
    "own held-out test set.",
    "Automate the active-learning feedback loop into a scheduled retraining pipeline with model "
    "versioning.",
]
story.append(ListFlowable([ListItem(body(f)) for f in future], bulletType="1", leftIndent=14))
story.append(PageBreak())

# ============================================================= 21. CONCLUSION
story.append(h1("21. Conclusion", "conclusion"))
story.append(body(
    "UrduStack demonstrates a working, evaluated approach to a genuine gap in existing NLP "
    "tooling: scam and harassment detection for the code-switched Roman Urdu, Urdu-script, and "
    "English text that Pakistani users actually write. Its central technical claim — that a "
    "fine-tuned transformer adds real value over keyword matching — is not merely asserted but "
    "measured: on vocabulary the heuristic layer cannot see at all, the trained model correctly "
    "generalizes on the majority of novel cases tested. Equally, the system's real gaps are reported "
    "with the same evidentiary standard as its successes, including one — a missed death threat — "
    "serious enough to be named as the project's top priority rather than smoothed over. The result "
    "is a system that is genuinely useful today across three real interfaces, with a clearly "
    "documented, honestly scoped path to being more complete."
))
story.append(PageBreak())

# ============================================================= REFERENCES
story.append(h1("References", "references"))
refs = [
    "Conneau, A. et al. (2020). Unsupervised Cross-lingual Representation Learning at Scale "
    "(XLM-RoBERTa). Proceedings of ACL.",
    "Hu, E. J. et al. (2021). LoRA: Low-Rank Adaptation of Large Language Models. arXiv:2106.09685.",
    "Pan, X. et al. (2017). Cross-lingual Name Tagging and Linking for 282 Languages (WikiAnn). "
    "Proceedings of ACL.",
    "Radford, A. et al. (2022). Robust Speech Recognition via Large-Scale Weak Supervision (Whisper). "
    "OpenAI.",
    "Hugging Face Hub datasets: Mavkif/Roman-Urdu-Parl-split; hafiz-hassaan-saeed/Roman-Urdu-Toxic-Corpus; "
    "community-datasets/roman_urdu_hate_speech; hamza-amin/urdu-spam-dataset.",
    "FastAPI, Gradio, PyTorch, Hugging Face Transformers, and PEFT open-source project documentation.",
]
story.append(ListFlowable([ListItem(Paragraph(r, styles["Small"])) for r in refs], bulletType="1", leftIndent=14))
story.append(PageBreak())

# ============================================================= APPENDIX
story.append(h1("Appendix A: Full API Endpoint Reference", "appendixA"))
story.append(styled_table(api_rows, col_widths=[1.6 * cm, 3.2 * cm, 9.2 * cm], font_size=8.9))
story.append(Spacer(1, 14))

story.append(h1("Appendix B: Repository Structure (abridged)", "appendixB"))
struct = """app/main.py                  FastAPI entrypoint
app/api/endpoints.py         8 API routes
app/models/risk_model.py     LoRA risk scorer + max-ensemble
app/models/ner_model.py      NER wrapper
app/models/model_manager.py  Orchestration, recommendation logic
app/utils/normalization.py   Code-switch normalization cascade
app/utils/risk.py            Heuristic scorer, threat categorization
app/utils/simplify.py        Plain-language simplification
app/utils/transcription.py   Whisper speech-to-text
scripts/train_risk_model.py  LoRA fine-tuning + calibration
tests/                       46 unit tests + evaluation/adversarial harnesses
playground.py                Gradio 4-tab demo
whatsapp_bot.py               Flask + Twilio WhatsApp bot
static/index.html            Self-contained website"""
story.append(Paragraph(struct.replace("\n", "<br/>"), styles["Quote"]))

# ============================================================= BUILD (multiBuild resolves TOC over multiple passes)
doc.multiBuild(story)
print("Saved", OUT)
