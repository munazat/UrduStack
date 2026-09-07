"""Builds the 10-slide hackathon presentation as a .pptx.

One-off build script — not part of the app. Run with:
    python docs/presentation/build_deck.py
Produces docs/presentation/UrduStack_Presentation.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
import copy

# ---- palette ----
INK = RGBColor(0x11, 0x18, 0x27)
SUBTLE = RGBColor(0x6b, 0x72, 0x80)
WHITE = RGBColor(0xff, 0xff, 0xff)
TEAL = RGBColor(0x0f, 0x76, 0x6e)
TEAL_LIGHT = RGBColor(0xf0, 0xfd, 0xfa)
TEAL_BORDER = RGBColor(0x5e, 0xea, 0xd4)
RED = RGBColor(0xdc, 0x26, 0x26)
RED_LIGHT = RGBColor(0xfe, 0xf2, 0xf2)
RED_BORDER = RGBColor(0xfc, 0xa5, 0xa5)
BLUE = RGBColor(0x1e, 0x3a, 0x8a)
BLUE_LIGHT = RGBColor(0xef, 0xf6, 0xff)
BLUE_BORDER = RGBColor(0x93, 0xc5, 0xfd)
PURPLE = RGBColor(0x58, 0x1c, 0x87)
PURPLE_LIGHT = RGBColor(0xfd, 0xf4, 0xff)
PURPLE_BORDER = RGBColor(0xe9, 0xd5, 0xff)
AMBER = RGBColor(0x78, 0x35, 0x0f)
AMBER_LIGHT = RGBColor(0xff, 0xfb, 0xeb)
AMBER_BORDER = RGBColor(0xfd, 0xe6, 0x8a)
GREEN = RGBColor(0x06, 0x5f, 0x46)
GREEN_LIGHT = RGBColor(0xec, 0xfd, 0xf5)
GREEN_BORDER = RGBColor(0x6e, 0xe7, 0xb7)
GRAY_LIGHT = RGBColor(0xf9, 0xfa, 0xfb)
GRAY_BORDER = RGBColor(0xe5, 0xe7, 0xeb)

SW, SH = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width = SW
prs.slide_height = SH
BLANK = prs.slide_layouts[6]


def add_slide():
    return prs.slides.add_slide(BLANK)


def bg(slide, color=WHITE):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def box(slide, x, y, w, h, fill=None, line=None, line_w=1.0, radius=True, shadow=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    sp = slide.shapes.add_shape(shape_type, x, y, w, h)
    if radius:
        try:
            sp.adjustments[0] = 0.06
        except Exception:
            pass
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(line_w)
    sp.shadow.inherit = False
    return sp


def text(slide, x, y, w, h, s, size=20, color=INK, bold=False, align=PP_ALIGN.LEFT,
          font="Segoe UI", anchor=MSO_ANCHOR.TOP, line_spacing=1.08, italic=False):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    lines = s.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.name = font
        r.font.color.rgb = color
    return tb


def rich_text(slide, x, y, w, h, runs_per_line, size=20, color=INK, align=PP_ALIGN.LEFT,
               font="Segoe UI", anchor=MSO_ANCHOR.TOP, line_spacing=1.1, space_after=6):
    """runs_per_line: list of list of (text, bold, color_or_None) tuples."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, line in enumerate(runs_per_line):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after)
        for chunk, bold, col in line:
            r = p.add_run()
            r.text = chunk
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.name = font
            r.font.color.rgb = col if col else color
    return tb


def bullets(slide, x, y, w, h, items, size=20, color=INK, font="Segoe UI",
            bullet_char="•  ", space_after=10, line_spacing=1.12):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after)
        if isinstance(item, tuple):
            head, sub = item
            r = p.add_run()
            r.text = bullet_char + head
            r.font.size = Pt(size)
            r.font.bold = True
            r.font.name = font
            r.font.color.rgb = color
            if sub:
                p2 = tf.add_paragraph()
                p2.space_after = Pt(space_after)
                r2 = p2.add_run()
                r2.text = "     " + sub
                r2.font.size = Pt(size - 4)
                r2.font.name = font
                r2.font.color.rgb = SUBTLE
        else:
            r = p.add_run()
            r.text = bullet_char + item
            r.font.size = Pt(size)
            r.font.name = font
            r.font.color.rgb = color
    return tb


def header(slide, title, subtitle=None, kicker=None):
    if kicker:
        text(slide, Inches(0.6), Inches(0.32), Inches(8), Inches(0.4), kicker,
             size=14, bold=True, color=TEAL, font="Segoe UI")
    text(slide, Inches(0.6), Inches(0.58) if kicker else Inches(0.42), Inches(11.5), Inches(0.9),
         title, size=34, bold=True, color=INK)
    if subtitle:
        text(slide, Inches(0.6), Inches(1.24), Inches(12), Inches(0.5), subtitle,
             size=16, color=SUBTLE)
    box(slide, Inches(0.6), Inches(1.66), Inches(12.13), Pt(2.2), fill=TEAL_BORDER, radius=False)


def footer(slide, n):
    text(slide, Inches(0.6), Inches(7.14), Inches(6), Inches(0.3), "UrduStack",
         size=11, color=SUBTLE)
    text(slide, Inches(11.9), Inches(7.14), Inches(0.9), Inches(0.3), str(n),
         size=11, color=SUBTLE, align=PP_ALIGN.RIGHT)


def pic_fit(slide, path, x, y, max_w, max_h):
    from PIL import Image
    with Image.open(path) as im:
        iw, ih = im.size
    ar = iw / ih
    w, h = max_w, max_w / ar
    if h > max_h:
        h = max_h
        w = max_h * ar
    px = x + (max_w - w) / 2
    py = y + (max_h - h) / 2
    slide.shapes.add_picture(path, px, py, width=int(w), height=int(h))


# ============================================================ SLIDE 1 — TITLE
s = add_slide()
bg(s, INK)
box(s, Inches(0), Inches(0), SW, Inches(0.12), fill=TEAL, radius=False)
text(s, Inches(0.9), Inches(2.3), Inches(11.5), Inches(0.6), "🇵🇰  URDUSTACK", size=20, bold=True, color=TEAL_BORDER)
text(s, Inches(0.9), Inches(2.85), Inches(11.5), Inches(1.5), "UrduStack", size=64, bold=True, color=WHITE)
text(s, Inches(0.9), Inches(3.9), Inches(11.5), Inches(0.9),
     "Stop Roman-Urdu job scams before the click.", size=26, color=TEAL_BORDER, bold=True)
text(s, Inches(0.9), Inches(4.55), Inches(11.0), Inches(0.6),
     "Code-switch-aware Urdu NLP infrastructure for scam and harassment detection", size=18, color=RGBColor(0xd1, 0xd5, 0xdb))

box(s, Inches(0.9), Inches(5.7), Inches(5.4), Inches(1.0), fill=RGBColor(0x1f, 0x29, 0x37), radius=True)
text(s, Inches(1.15), Inches(5.85), Inches(5.0), Inches(0.35), "Shahoud Shahid", size=20, bold=True, color=WHITE)
text(s, Inches(1.15), Inches(6.22), Inches(5.0), Inches(0.35), "Team", size=13, color=SUBTLE)

box(s, Inches(6.5), Inches(5.7), Inches(5.4), Inches(1.0), fill=RGBColor(0x1f, 0x29, 0x37), radius=True)
text(s, Inches(6.75), Inches(5.85), Inches(5.0), Inches(0.35), "Munaza Tariq", size=20, bold=True, color=WHITE)
text(s, Inches(6.75), Inches(6.22), Inches(5.0), Inches(0.35), "Team", size=13, color=SUBTLE)

footer(s, 1)

# ============================================================ SLIDE 2 — PROBLEM
s = add_slide()
bg(s)
header(s, "The Problem", "Pakistani digital text defeats English-only, keyword-based moderation")

box(s, Inches(0.6), Inches(1.95), Inches(5.9), Inches(2.1), fill=RED_LIGHT, line=RED_BORDER)
text(s, Inches(0.85), Inches(2.12), Inches(5.4), Inches(0.4), "A real scam ad, verbatim", size=18, bold=True, color=RGBColor(0x7f,0x1d,0x1d))
text(s, Inches(0.85), Inches(2.62), Inches(5.4), Inches(1.0),
     '"Urgent hiring! 50000 per week,\nsend processing fee to register."',
     size=20, color=INK, font="Consolas")
text(s, Inches(0.85), Inches(3.65), Inches(5.4), Inches(0.35),
     "Roman Urdu / English — no Urdu script at all", size=14, italic=True, color=SUBTLE)

box(s, Inches(6.75), Inches(1.95), Inches(5.98), Inches(2.1), fill=BLUE_LIGHT, line=BLUE_BORDER)
text(s, Inches(7.0), Inches(2.12), Inches(5.4), Inches(0.4), "Three scripts, one sentence", size=18, bold=True, color=BLUE)
bullets(s, Inches(7.0), Inches(2.62), Inches(5.5), Inches(1.4), [
    "Urdu script, Roman Urdu, and English mix freely",
    "Often within the same message, sometimes the same sentence",
], size=17, color=INK, space_after=8)

bullets(s, Inches(0.6), Inches(4.35), Inches(12.1), Inches(2.5), [
    ("English-only keyword filters miss it entirely",
     "\"processing fee\" still slips past leetspeak, spacing tricks, and misspellings"),
    ("The harm is real and documented",
     "Fake job postings on Facebook, WhatsApp, and OLX target Pakistani students and jobseekers who lose money to advance-fee scams — alongside abusive and harassing content in the same mixed script"),
], size=20, color=INK, space_after=16)

footer(s, 2)

# ============================================================ SLIDE 3 — SOLUTION
s = add_slide()
bg(s)
header(s, "Proposed Solution", "Normalize the code-switching first, then score with a model trained for it")

bullets(s, Inches(0.6), Inches(1.95), Inches(6.0), Inches(4.4), [
    ("Normalize first", "Roman Urdu / English / Urdu script → one consistent Urdu-script representation"),
    ("Score with a real trained model", "LoRA-tuned XLM-RoBERTa + a hardened heuristic layer, combined — not a keyword list"),
    ("Explain the verdict", "Shows which phrases drove the score, the threat type, and specific next steps"),
    ("Self-hosted, on-device", "No data leaves the deployment, $0 per request, sub-second latency"),
], size=19, color=INK, space_after=18)

box(s, Inches(6.9), Inches(1.95), Inches(5.83), Inches(4.4), fill=GRAY_LIGHT, line=GRAY_BORDER)
text(s, Inches(7.15), Inches(2.12), Inches(5.3), Inches(0.4), "Why not just prompt GPT-4o?", size=18, bold=True, color=INK)

rows = [
    ("", "UrduStack", "GPT-4o API"),
    ("Cost / request", "$0", "~$0.01–0.03"),
    ("Data stays local", "Yes", "No"),
    ("Latency", "Sub-second", "1–3 s"),
    ("Offline capable", "Yes", "No"),
]
top = 2.65
for i, (a, b, c) in enumerate(rows):
    y = Inches(top + i * 0.62)
    if i == 0:
        box(s, Inches(7.15), y, Inches(5.35), Inches(0.55), fill=TEAL)
        text(s, Inches(7.3), y + Inches(0.08), Inches(2.2), Inches(0.4), b, size=15, bold=True, color=WHITE)
        text(s, Inches(9.9), y + Inches(0.08), Inches(2.4), Inches(0.4), c, size=15, bold=True, color=WHITE)
    else:
        fill = WHITE if i % 2 else RGBColor(0xf3, 0xf4, 0xf6)
        box(s, Inches(7.15), y, Inches(5.35), Inches(0.55), fill=fill, line=GRAY_BORDER, line_w=0.5)
        text(s, Inches(7.3), y + Inches(0.1), Inches(2.3), Inches(0.35), a, size=13.5, color=SUBTLE)
        text(s, Inches(9.9), y + Inches(0.1), Inches(1.2), Inches(0.35), b, size=14, bold=True, color=TEAL)
        text(s, Inches(11.1), y + Inches(0.1), Inches(1.3), Inches(0.35), c, size=14, color=RGBColor(0x99,0x1b,0x1b))

footer(s, 3)

# ============================================================ SLIDE 4 — FEATURES
s = add_slide()
bg(s)
header(s, "Key Features", "Six implemented capabilities, verified end-to-end against the real trained model")

feats = [
    ("\U0001F524", "Code-Switch Normalization", "Dictionary + FAISS retrieval + phonetic fallback", BLUE_LIGHT, BLUE_BORDER, BLUE),
    ("\U0001F6E1", "Explainable Risk Scoring", "LoRA model + heuristic ensemble, F1 87.1%", RED_LIGHT, RED_BORDER, RGBColor(0x7f,0x1d,0x1d)),
    ("\U0001F3F7", "Multi-Category Threat Type", "Job scam / phishing / harassment, each with advice", PURPLE_LIGHT, PURPLE_BORDER, PURPLE),
    ("\U0001F464", "Named Entity Recognition", "PERSON / LOCATION / ORGANIZATION — informational", TEAL_LIGHT, TEAL_BORDER, TEAL),
    ("\U0001F399", "Speech-to-Text", "Whisper transcribes spoken Urdu into the pipeline", AMBER_LIGHT, AMBER_BORDER, AMBER),
    ("\U0001F4AC", "Plain-Language Simplify", "Rewrites verdicts into everyday Urdu", GREEN_LIGHT, GREEN_BORDER, GREEN),
]
cols, rows_n = 3, 2
cw, ch = Inches(3.95), Inches(1.95)
gx, gy = Inches(0.6), Inches(2.0)
for i, (icon, title, sub, fillc, linec, txtc) in enumerate(feats):
    r, c = divmod(i, cols)
    x = gx + c * (cw + Inches(0.15))
    y = gy + r * (ch + Inches(0.2))
    box(s, x, y, cw, ch, fill=fillc, line=linec)
    text(s, x + Inches(0.22), y + Inches(0.18), Inches(1.0), Inches(0.6), icon, size=30)
    text(s, x + Inches(0.22), y + Inches(0.78), cw - Inches(0.44), Inches(0.55), title, size=17, bold=True, color=txtc)
    text(s, x + Inches(0.22), y + Inches(1.32), cw - Inches(0.44), Inches(0.55), sub, size=13, color=INK)

footer(s, 4)

# ============================================================ SLIDE 5 — ARCHITECTURE
s = add_slide()
bg(s)
header(s, "System Architecture", "One FastAPI process, one ModelManager, three real entry points, no external database")

layers = [
    ("Entry Surfaces", ["Website", "Gradio Playground", "WhatsApp Bot"], BLUE_LIGHT, BLUE_BORDER, BLUE),
    ("FastAPI Layer", ["/normalize", "/risk-score", "/ner", "/analyze", "/feedback"], AMBER_LIGHT, AMBER_BORDER, AMBER),
    ("ModelManager", ["Lazy-loads models", "Orchestrates pipeline", "Graceful fallback"], PURPLE_LIGHT, PURPLE_BORDER, PURPLE),
    ("Core Modules", ["Normalizer", "Risk Scorer", "NER", "STT", "Simplify"], GREEN_LIGHT, GREEN_BORDER, GREEN),
    ("Models & Data", ["LoRA adapter (4.5 MB)", "485-word dictionary", "feedback.csv"], RED_LIGHT, RED_BORDER, RGBColor(0x7f,0x1d,0x1d)),
]
y0 = Inches(1.95)
lh = Inches(0.92)
gap = Inches(0.12)
row_w = 9.38          # inches, the white row container width
row_start_x = 3.55     # inches, where chips begin
row_end_x = 3.35 + row_w - 0.2   # leave a margin before the row's right edge
for i, (name, items, fillc, linec, txtc) in enumerate(layers):
    y = y0 + i * (lh + gap)
    box(s, Inches(0.6), y, Inches(2.55), lh, fill=fillc, line=linec)
    text(s, Inches(0.78), y + Inches(0.1), Inches(2.2), Inches(0.35), f"{i+1}", size=14, bold=True, color=txtc)
    text(s, Inches(0.78), y + Inches(0.36), Inches(2.2), Inches(0.5), name, size=15, bold=True, color=txtc)
    box(s, Inches(3.35), y, Inches(row_w), lh, fill=WHITE, line=linec, line_w=0.75)

    # Fit chips to the available row width: shrink per-char width and gap
    # until the total fits, rather than a fixed formula that can overflow.
    n = len(items)
    for char_w, gap_w, base in [(0.105, 0.14, 0.3), (0.09, 0.10, 0.24), (0.078, 0.08, 0.2)]:
        widths = [base + char_w * len(it) for it in items]
        total = sum(widths) + gap_w * (n - 1)
        if total <= (row_end_x - row_start_x):
            break
    chip_x = row_start_x
    for it, w_in in zip(items, widths):
        w = Inches(w_in)
        box(s, chip_x, y + Inches(0.24), w, Inches(0.46), fill=fillc, line=None)
        text(s, chip_x, y + Inches(0.24), w, Inches(0.46), it, size=12.5, color=txtc, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        chip_x = chip_x + w + Inches(gap_w)
    if i < len(layers) - 1:
        arrow = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(1.78), y + lh - Inches(0.02), Inches(0.3), gap + Inches(0.05))
        arrow.fill.solid(); arrow.fill.fore_color.rgb = SUBTLE; arrow.line.fill.background()

text(s, Inches(0.6), Inches(6.85), Inches(12), Inches(0.35),
     "Self-hosted: Docker → Hugging Face Spaces, or Colab T4 GPU with a public share link.", size=13, italic=True, color=SUBTLE)
footer(s, 5)

# ============================================================ SLIDE 6 — HOW IT WORKS
s = add_slide()
bg(s)
header(s, "How It Works", "One request, six pipeline stages — analyze_text() in app/models/model_manager.py")

stages = [
    ("1", "Normalize", "Code-switched text →\nUrdu script", BLUE_LIGHT, BLUE_BORDER, BLUE),
    ("2", "Risk Score", "Max-ensemble:\nLoRA vs. heuristic", RED_LIGHT, RED_BORDER, RGBColor(0x7f,0x1d,0x1d)),
    ("3", "NER", "Extract PERSON /\nLOCATION / ORG", TEAL_LIGHT, TEAL_BORDER, TEAL),
    ("4", "Categorize", "Job scam / phishing /\nharassment", PURPLE_LIGHT, PURPLE_BORDER, PURPLE),
    ("5", "Simplify", "Plain-language\nUrdu explanation", AMBER_LIGHT, AMBER_BORDER, AMBER),
    ("6", "Recommend", "Actionable,\ncategory-specific advice", GREEN_LIGHT, GREEN_BORDER, GREEN),
]
bw, bh = Inches(1.85), Inches(2.6)
bx, by = Inches(0.55), Inches(2.15)
for i, (n, name, desc, fillc, linec, txtc) in enumerate(stages):
    x = bx + i * (bw + Inches(0.16))
    box(s, x, by, bw, bh, fill=fillc, line=linec)
    circ = s.shapes.add_shape(MSO_SHAPE.OVAL, x + Inches(0.65), by + Inches(0.18), Inches(0.55), Inches(0.55))
    circ.fill.solid(); circ.fill.fore_color.rgb = txtc; circ.line.fill.background()
    ctf = circ.text_frame; ctf.margin_left=0; ctf.margin_right=0; ctf.margin_top=0; ctf.margin_bottom=0
    cp = ctf.paragraphs[0]; cp.alignment = PP_ALIGN.CENTER
    cr = cp.add_run(); cr.text = n; cr.font.size = Pt(18); cr.font.bold = True; cr.font.color.rgb = WHITE
    text(s, x + Inches(0.1), by + Inches(0.85), bw - Inches(0.2), Inches(0.4), name, size=16, bold=True, color=txtc, align=PP_ALIGN.CENTER)
    text(s, x + Inches(0.1), by + Inches(1.35), bw - Inches(0.2), Inches(1.1), desc, size=13, color=INK, align=PP_ALIGN.CENTER)
    if i < len(stages) - 1:
        ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + bw - Inches(0.02), by + bh/2 - Inches(0.1), Inches(0.2), Inches(0.2))
        ar.fill.solid(); ar.fill.fore_color.rgb = SUBTLE; ar.line.fill.background()

box(s, Inches(0.6), Inches(5.15), Inches(12.13), Inches(1.55), fill=GRAY_LIGHT, line=GRAY_BORDER)
text(s, Inches(0.85), Inches(5.32), Inches(11.6), Inches(0.4), "Example, live:", size=15, bold=True, color=INK)
text(s, Inches(0.85), Inches(5.68), Inches(11.6), Inches(0.45),
     '"job available 50000 per week send processing fee"  →  score 1.00, HIGH, "Fake Job Posting"',
     size=17, color=TEAL, font="Consolas")
text(s, Inches(0.85), Inches(6.15), Inches(11.6), Inches(0.4),
     "Every stage runs in-process — no external API calls, sub-second response.", size=13, italic=True, color=SUBTLE)

footer(s, 6)

# ============================================================ SLIDE 7 — TECHNICAL IMPLEMENTATION
s = add_slide()
bg(s)
header(s, "Technical Implementation", "Real technologies, real numbers — every figure below is from a committed, reproducible test run")

col1 = [
    ("Base model", "xlm-roberta-base — 270M parameters"),
    ("Fine-tuning", "LoRA, r=16, α=32 → 4.5 MB adapter"),
    ("Training data", "~80k rows: PURUTT (72.7k) + synthetic scam (1.5k) + supplementary"),
    ("Calibration", "Temperature scaling, T = 1.409 (grid search, 100 values)"),
]
col2 = [
    ("Framework", "FastAPI + Pydantic, PEFT, Transformers, PyTorch"),
    ("NER", "XLM-RoBERTa fine-tuned on WikiAnn"),
    ("Speech-to-text", "OpenAI Whisper (base)"),
    ("Retrieval", "FAISS + char-3-gram TF-IDF for fuzzy normalization"),
]
text(s, Inches(0.6), Inches(1.95), Inches(5.9), Inches(0.4), "Model & Training", size=17, bold=True, color=TEAL)
y = 2.42
for t, d in col1:
    text(s, Inches(0.6), Inches(y), Inches(5.9), Inches(0.35), t, size=15, bold=True, color=INK)
    text(s, Inches(0.6), Inches(y+0.34), Inches(5.9), Inches(0.5), d, size=13, color=SUBTLE)
    y += 0.95

text(s, Inches(6.9), Inches(1.95), Inches(5.9), Inches(0.4), "Stack & Tooling", size=17, bold=True, color=TEAL)
y = 2.42
for t, d in col2:
    text(s, Inches(6.9), Inches(y), Inches(5.9), Inches(0.35), t, size=15, bold=True, color=INK)
    text(s, Inches(6.9), Inches(y+0.34), Inches(5.9), Inches(0.5), d, size=13, color=SUBTLE)
    y += 0.95

box(s, Inches(0.6), Inches(6.35), Inches(12.13), Inches(0.75), fill=TEAL, radius=True)
text(s, Inches(0.9), Inches(6.5), Inches(11.6), Inches(0.5),
     "Verified: 89.7% accuracy · 87.1% F1 (107 test examples) · 12/12 adversarial cases · 46/46 unit tests",
     size=15, bold=True, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)

footer(s, 7)

# ============================================================ SLIDE 8 — UI/UX DEMO
s = add_slide()
bg(s)
header(s, "UI/UX & Demonstration", "Real, live output — not a mockup")

pic_fit(s, "docs/screenshots/04_gradio_result.png", Inches(0.55), Inches(1.95), Inches(7.6), Inches(5.05))
box(s, Inches(0.55), Inches(1.95), Inches(7.6), Inches(5.05), fill=None, line=GRAY_BORDER, line_w=1.0)

text(s, Inches(8.35), Inches(1.95), Inches(4.4), Inches(0.4), "What the user sees", size=17, bold=True, color=TEAL)
bullets(s, Inches(8.35), Inches(2.4), Inches(4.4), Inches(4.5), [
    "Paste any suspicious text — Roman Urdu, Urdu script, or English mix",
    "Risk verdict with score and confidence, in one glance",
    "Threat type: fake job posting, phishing, or harassment",
    "Exactly which phrases drove the score, with weights",
    "Normalized Urdu-script text, and a plain-language explanation",
    "A specific recommendation — not just a red flag",
    "Optional feedback loop feeds future retraining",
], size=14.5, color=INK, space_after=10)

footer(s, 8)

# ============================================================ SLIDE 9 — IMPACT
s = add_slide()
bg(s)
header(s, "Impact & Benefits", "Built for the people existing tools don't cover")

bullets(s, Inches(0.6), Inches(1.95), Inches(5.9), Inches(4.5), [
    ("Protects a real, underserved population", "Roman-Urdu speakers fall through the gap between English moderation and Urdu-script-only tools"),
    ("Explainable, not a black box", "Users see why a message was flagged — builds trust, and teaches pattern recognition over time"),
    ("Meets people where scams land", "Website, Gradio demo, and a WhatsApp bot — not locked behind a developer-only API"),
    ("Zero marginal cost, private by design", "Self-hosted; no per-request fee, no data sent to a third-party API"),
], size=18, color=INK, space_after=16)

box(s, Inches(6.9), Inches(1.95), Inches(5.83), Inches(4.5), fill=GREEN_LIGHT, line=GREEN_BORDER)
text(s, Inches(7.15), Inches(2.15), Inches(5.3), Inches(0.4), "Scalability & future potential", size=17, bold=True, color=GREEN)
bullets(s, Inches(7.15), Inches(2.65), Inches(5.3), Inches(3.6), [
    "Same architecture extends to other code-switched, under-resourced languages",
    "Active-learning feedback loop already collects real corrections for retraining",
    "Multi-category detection can expand to lottery, charity, investment, and loan scams — synthetic data for all 7 already exists",
    "WhatsApp bot is the highest-leverage distribution channel — reaches victims, not just judges",
], size=15, color=INK, space_after=12)

footer(s, 9)

# ============================================================ SLIDE 10 — CONCLUSION
s = add_slide()
bg(s, INK)
box(s, Inches(0), Inches(0), SW, Inches(0.12), fill=TEAL, radius=False)
text(s, Inches(0.7), Inches(0.55), Inches(11.5), Inches(0.8), "Conclusion & Future Vision", size=32, bold=True, color=WHITE)
box(s, Inches(0.7), Inches(1.35), Inches(11.93), Pt(2.2), fill=TEAL_BORDER, radius=False)

text(s, Inches(0.7), Inches(1.65), Inches(5.9), Inches(0.4), "What we achieved", size=18, bold=True, color=TEAL_BORDER)
bullets(s, Inches(0.7), Inches(2.1), Inches(5.9), Inches(4.3), [
    "A working, code-switch-aware detection pipeline — trained, calibrated, and evaluated on real data",
    "Verified semantic generalization beyond keyword matching, not just claimed",
    "Three real, working surfaces sharing one decision engine",
    "Honest, evidence-backed documentation of what works and what doesn't yet",
], size=16.5, color=WHITE, space_after=14)

text(s, Inches(7.0), Inches(1.65), Inches(5.6), Inches(0.4), "What's next", size=18, bold=True, color=TEAL_BORDER)
bullets(s, Inches(7.0), Inches(2.1), Inches(5.6), Inches(4.3), [
    "Close the remaining threat-detection gaps with targeted retraining",
    "Ship the full 6.37M-sentence frequency map for Tier-1 normalization",
    "Move the WhatsApp bot from demo-time to a persistent, always-on deployment",
    "Expand multi-category detection to all 7 scam types already in the training data generator",
], size=16.5, color=WHITE, space_after=14)

box(s, Inches(0.7), Inches(6.55), Inches(11.93), Inches(0.65), fill=TEAL, radius=True)
text(s, Inches(0.7), Inches(6.68), Inches(11.93), Inches(0.4),
     "UrduStack — because the language your users actually type in deserves real protection.",
     size=17, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

text(s, Inches(0.7), Inches(7.14), Inches(6), Inches(0.3), "UrduStack", size=11, color=SUBTLE)
text(s, Inches(11.9), Inches(7.14), Inches(0.9), Inches(0.3), "10", size=11, color=SUBTLE, align=PP_ALIGN.RIGHT)

import os, time
out_path = "docs/presentation/UrduStack_Presentation.pptx"
tmp_path = "docs/presentation/_build_tmp.pptx"
prs.save(tmp_path)
for attempt in range(6):
    try:
        if os.path.exists(out_path):
            os.remove(out_path)
        os.rename(tmp_path, out_path)
        break
    except PermissionError:
        time.sleep(1)
else:
    out_path = tmp_path
print("Saved", out_path, "—", len(prs.slides.__iter__.__self__._sldIdLst), "slides")
