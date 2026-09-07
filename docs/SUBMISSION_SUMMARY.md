# Submission Form — Project Summary Field

Paste the text below into the "Project summary" field of the submission form
(200–1,500 characters; current length noted below).

---

UrduStack stops Roman-Urdu job scams and harassment before the click. Pakistani
digital text mixes Urdu script, Roman Urdu, and English in one sentence — a
pattern that defeats English-only keyword filters. UrduStack normalizes that
code-switched text into Urdu script, then classifies it with a LoRA-fine-tuned
XLM-RoBERTa model combined with a hardened heuristic layer, not a keyword list.
It explains every verdict (which phrases drove the score), classifies the
threat type (fake job posting, phishing, or harassment), and gives a specific,
actionable recommendation — reachable via a website, a Gradio demo, and a
WhatsApp bot, all sharing one scoring engine.

Built for and by a two-person team, the system reaches 89.7% accuracy and an
F1 of 87.1% on a held-out test set, and passes 12/12 adversarial red-team
cases against the real deployed model — 8 of them driven by the trained model
independently, not the keyword layer. On 11 phrases matching none of the
heuristic's known patterns, the model correctly generalizes on 7, evidence of
real semantic understanding rather than memorization. Runs entirely
on-device: $0 per request, no data leaves the deployment. Known gaps —
including one serious miss on a direct threat — are documented openly rather
than hidden, alongside a clear roadmap to close them.

---

**Character count: 1,315** (within the 200–1,500 limit)
