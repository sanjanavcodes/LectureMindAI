"""
LectureMind AI — app.py
=======================
100% FREE · OFFLINE · NO API KEY REQUIRED
NLP summarisation engine using:
  - sumy        → extractive summarisation (LexRank + LSA)
  - nltk        → tokenisation, stopwords, sentence splitting
  - scikit-learn → TF-IDF keyword/concept extraction
  - PyMuPDF     → PDF text extraction
  - python-docx → DOCX text extraction

Routes: /  /summarize  /quiz  /simplify  /exam-mode
"""

import io
import re
import string
import logging
import collections

from flask import Flask, render_template, request, jsonify

# ── File extraction libraries ─────────────────────────────────────────────────
try:
    import fitz          # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document as DocxDocument
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

# ── NLP: NLTK ─────────────────────────────────────────────────────────────────
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

# Download required NLTK data on first run (cached locally afterwards)
for _pkg in ("punkt", "punkt_tab", "stopwords", "averaged_perceptron_tagger"):
    try:
        nltk.data.find(f"tokenizers/{_pkg}" if "punkt" in _pkg
                       else f"corpora/{_pkg}" if _pkg == "stopwords"
                       else f"taggers/{_pkg}")
    except LookupError:
        nltk.download(_pkg, quiet=True)

# ── NLP: sumy ─────────────────────────────────────────────────────────────────
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers   import Tokenizer as SumyTokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.lsa      import LsaSummarizer
from sumy.nlp.stemmers         import Stemmer
from sumy.utils                import get_stop_words

# ── NLP: scikit-learn TF-IDF ─────────────────────────────────────────────────
from sklearn.feature_extraction.text import TfidfVectorizer

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024   # 16 MB

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(asctime)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

LANGUAGE   = "english"
STOP_WORDS = set(stopwords.words("english"))


# ════════════════════════════════════════════════════════════════════════════════
#  TEXT EXTRACTION
# ════════════════════════════════════════════════════════════════════════════════

def extract_text_from_file(file_storage) -> str:
    """Extract plain text from a PDF, DOCX, or TXT FileStorage object."""
    filename  = file_storage.filename.lower()
    raw_bytes = file_storage.read()

    log.debug("File received: %s (%d bytes)", file_storage.filename, len(raw_bytes))

    if not raw_bytes:
        raise ValueError("The uploaded file is empty.")

    # ── PDF ──────────────────────────────────────────────────────────────────
    if filename.endswith(".pdf"):
        if not PDF_SUPPORT:
            raise ValueError("PDF support requires PyMuPDF. Run: pip install pymupdf")
        try:
            doc   = fitz.open(stream=raw_bytes, filetype="pdf")
            pages = [page.get_text() for page in doc]
            text  = "\n".join(pages).strip()
            log.debug("PDF extracted — %d pages, %d chars", len(pages), len(text))
        except Exception as exc:
            raise ValueError(f"Could not read PDF (possibly corrupted): {exc}") from exc

    # ── DOCX ─────────────────────────────────────────────────────────────────
    elif filename.endswith(".docx"):
        if not DOCX_SUPPORT:
            raise ValueError("DOCX support requires python-docx. Run: pip install python-docx")
        try:
            doc   = DocxDocument(io.BytesIO(raw_bytes))
            paras = [p.text for p in doc.paragraphs if p.text.strip()]
            text  = "\n".join(paras).strip()
            log.debug("DOCX extracted — %d paragraphs, %d chars", len(paras), len(text))
        except Exception as exc:
            raise ValueError(f"Could not read DOCX (possibly corrupted): {exc}") from exc

    # ── TXT ──────────────────────────────────────────────────────────────────
    elif filename.endswith(".txt"):
        text = ""
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                text = raw_bytes.decode(enc).strip()
                log.debug("TXT decoded with %s — %d chars", enc, len(text))
                break
            except UnicodeDecodeError:
                continue
        if not text:
            raise ValueError("Could not decode TXT file (unknown encoding).")

    else:
        raise ValueError(
            f"Unsupported file type '{file_storage.filename}'. "
            "Please upload a PDF, DOCX, or TXT file."
        )

    if not text:
        raise ValueError(
            "Text extraction produced no content. "
            "The file may be image-based (scanned PDF) or completely empty."
        )

    log.info("Extraction successful — %d characters", len(text))
    return text


def get_uploaded_text(req) -> str:
    """Return text from file upload, JSON body, or form field. Raises on empty."""
    if "file" in req.files and req.files["file"].filename:
        return extract_text_from_file(req.files["file"])

    text = (
        (req.get_json() or {}).get("text", "").strip()
        if req.is_json
        else req.form.get("text", "").strip()
    )
    if not text:
        raise ValueError("No content provided. Upload a file or paste some text.")

    log.debug("Pasted text received — %d chars", len(text))
    return text


# ════════════════════════════════════════════════════════════════════════════════
#  FREE NLP ENGINE  (no API, no key, 100% offline)
# ════════════════════════════════════════════════════════════════════════════════

def _clean(text: str) -> str:
    """Normalise whitespace and remove non-printable characters."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    return text.strip()


# ── 1. Extractive summary (sumy LexRank) ─────────────────────────────────────

def extractive_summary(text: str, sentence_count: int = 6) -> str:
    """
    Use sumy's LexRank algorithm to pick the most important sentences
    from the actual document. Different documents → different sentences.
    """
    cleaned = _clean(text)
    parser  = PlaintextParser.from_string(cleaned, SumyTokenizer(LANGUAGE))
    stemmer = Stemmer(LANGUAGE)

    summarizer = LexRankSummarizer(stemmer)
    summarizer.stop_words = get_stop_words(LANGUAGE)

    # Clamp sentence count so short docs don't crash
    total_sentences = len(parser.document.sentences)
    n = min(sentence_count, max(1, total_sentences))

    sentences = summarizer(parser.document, n)
    result    = " ".join(str(s) for s in sentences)

    log.debug("LexRank summary: %d sentences from %d total", n, total_sentences)
    return result


def lsa_summary(text: str, sentence_count: int = 4) -> str:
    """Secondary summary pass with LSA for diversity."""
    cleaned = _clean(text)
    parser  = PlaintextParser.from_string(cleaned, SumyTokenizer(LANGUAGE))
    stemmer = Stemmer(LANGUAGE)

    summarizer = LsaSummarizer(stemmer)
    summarizer.stop_words = get_stop_words(LANGUAGE)

    total_sentences = len(parser.document.sentences)
    n = min(sentence_count, max(1, total_sentences))

    sentences = summarizer(parser.document, n)
    return " ".join(str(s) for s in sentences)


# ── 2. TF-IDF keyword / concept extraction ───────────────────────────────────

def extract_keywords(text: str, top_n: int = 12) -> list[str]:
    """
    Split the document into chunks, run TF-IDF, and return the top-n
    terms specific to THIS document (not generic stopwords).
    """
    cleaned    = _clean(text)
    sentences  = sent_tokenize(cleaned)

    if len(sentences) < 2:
        # Fallback for very short text: simple frequency count
        words = [
            w.lower() for w in word_tokenize(cleaned)
            if w.lower() not in STOP_WORDS
            and w not in string.punctuation
            and len(w) > 3
        ]
        freq = collections.Counter(words)
        return [w for w, _ in freq.most_common(top_n)]

    # Group sentences into ~5-sentence chunks for TF-IDF
    chunk_size = 5
    chunks = [
        " ".join(sentences[i : i + chunk_size])
        for i in range(0, len(sentences), chunk_size)
    ]

    try:
        tfidf   = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),   # unigrams + bigrams
            max_features=300,
            min_df=1,
        )
        matrix  = tfidf.fit_transform(chunks)
        scores  = matrix.sum(axis=0).A1
        terms   = tfidf.get_feature_names_out()
        ranked  = sorted(zip(terms, scores), key=lambda x: x[1], reverse=True)
        keywords = [t for t, _ in ranked if len(t) > 3][:top_n]
    except Exception as exc:
        log.warning("TF-IDF failed (%s) — falling back to frequency count", exc)
        words    = [
            w.lower() for w in word_tokenize(cleaned)
            if w.lower() not in STOP_WORDS and w not in string.punctuation and len(w) > 3
        ]
        keywords = [w for w, _ in collections.Counter(words).most_common(top_n)]

    log.debug("Extracted %d keywords", len(keywords))
    return keywords


# ── 3. Key-point sentences ───────────────────────────────────────────────────

def extract_key_points(text: str, n: int = 8) -> list[str]:
    """
    Score every sentence by how many document-specific TF-IDF keywords it
    contains. Return the top-n scoring sentences in document order.
    """
    cleaned   = _clean(text)
    sentences = sent_tokenize(cleaned)
    keywords  = set(extract_keywords(text, top_n=20))

    def score(sent):
        words = set(word_tokenize(sent.lower()))
        return len(words & keywords)

    scored    = sorted(enumerate(sentences), key=lambda x: score(x[1]), reverse=True)
    top_idxs  = sorted([i for i, _ in scored[:n]])
    points    = [sentences[i].strip() for i in top_idxs if sentences[i].strip()]

    log.debug("Selected %d key-point sentences", len(points))
    return points


# ── 4. Quiz generation (sentence-completion style) ───────────────────────────

def generate_quiz(text: str, n: int = 5) -> list[dict]:
    """
    Build fill-in-the-blank / definition quiz questions from key sentences.
    Each question is 100% derived from the actual uploaded text.
    """
    cleaned   = _clean(text)
    sentences = sent_tokenize(cleaned)
    keywords  = extract_keywords(text, top_n=30)
    kw_set    = set(keywords)

    quiz      = []
    used_kws  = set()

    for sent in sentences:
        if len(quiz) >= n:
            break
        words     = word_tokenize(sent)
        sent_kws  = [w for w in words if w.lower() in kw_set and w.lower() not in used_kws]
        if not sent_kws:
            continue

        keyword   = sent_kws[0]
        used_kws.add(keyword.lower())

        # Create a blank-fill question
        blanked   = re.sub(
            r'\b' + re.escape(keyword) + r'\b',
            "______",
            sent,
            count=1,
            flags=re.IGNORECASE,
        )
        quiz.append({
            "q": f"Fill in the blank: {blanked}",
            "a": keyword,
            "difficulty": "easy" if len(quiz) < 2 else "medium" if len(quiz) < 4 else "hard",
        })

    # Pad with "What does X refer to?" style if fewer than n generated
    for kw in keywords:
        if len(quiz) >= n:
            break
        if kw in used_kws:
            continue
        # Find the sentence that contains the keyword → that is the answer context
        context = next(
            (s for s in sentences if re.search(r'\b' + re.escape(kw) + r'\b', s, re.IGNORECASE)),
            None,
        )
        if context:
            quiz.append({
                "q": f"What does the document say about '{kw}'?",
                "a": context.strip(),
                "difficulty": "medium",
            })
            used_kws.add(kw)

    log.debug("Generated %d quiz questions", len(quiz))
    return quiz


# ── 5. Simplification (sentence-level readability pass) ──────────────────────

def simplify_text(text: str) -> tuple[str, list[dict]]:
    """
    - Break long sentences at conjunctions/semicolons for readability.
    - Build a mini-glossary from TF-IDF bigrams that look like technical terms.
    Returns (simplified_text, glossary_list).
    """
    cleaned   = _clean(text)
    sentences = sent_tokenize(cleaned)
    simple    = []

    for sent in sentences:
        # Split on "; " or " and " / " but " / " which " for very long sentences
        if len(sent.split()) > 30:
            parts = re.split(r';\s+| and | but | which | because | however ', sent)
            parts = [p.strip().capitalize() for p in parts if p.strip()]
            simple.extend(parts)
        else:
            simple.append(sent.strip())

    simplified = " ".join(simple)

    # Glossary: bigram TF-IDF terms that are likely technical (title-case or all-lower > 5 chars)
    keywords = extract_keywords(text, top_n=20)
    glossary = []
    for kw in keywords:
        if len(kw) > 5 or " " in kw:  # prefer multi-word or longer terms
            # Find first sentence that contains it as the "definition"
            context = next(
                (s for s in sentences if re.search(r'\b' + re.escape(kw) + r'\b', s, re.IGNORECASE)),
                None,
            )
            if context:
                glossary.append({"term": kw, "definition": context.strip()})
        if len(glossary) >= 8:
            break

    log.debug("Simplification done — %d sentences, %d glossary items", len(simple), len(glossary))
    return simplified, glossary


# ── 6. Exam notes ─────────────────────────────────────────────────────────────

def generate_exam_notes(text: str) -> str:
    """Bullet-point revision notes drawn directly from the document's key sentences."""
    points = extract_key_points(text, n=8)
    return "\n".join(f"• {p}" for p in points)


# ── 7. Exam-mode package ──────────────────────────────────────────────────────

def generate_exam_package(text: str) -> dict:
    """Full exam prep: topic, key points, must-know terms, tips, cheat sheet."""
    keywords   = extract_keywords(text, top_n=15)
    key_points = extract_key_points(text, n=6)
    sentences  = sent_tokenize(_clean(text))

    # Derive topic from the two highest-scoring TF-IDF terms
    topic = " & ".join(keywords[:2]).title() if keywords else "Document Content"

    # Must-know: sentences containing the top 5 keywords
    must_know = []
    for kw in keywords[:5]:
        ctx = next(
            (s for s in sentences if re.search(r'\b' + re.escape(kw) + r'\b', s, re.IGNORECASE)),
            None,
        )
        if ctx:
            must_know.append(ctx.strip())

    # Exam tips: generic but driven by found keywords
    exam_tips = [
        f"Understand the concept of '{kw}' as described in the document."
        for kw in keywords[:4]
    ]

    cheat_sheet = "\n".join(f"• {p}" for p in key_points)

    return {
        "topic":           topic,
        "key_points":      key_points,
        "must_know":       must_know,
        "common_mistakes": [
            "Confusing related terms — review definitions carefully.",
            "Skipping over examples — they often appear in exam questions.",
            "Not reading the full context — answers depend on the whole passage.",
        ],
        "exam_tips":       exam_tips,
        "one_page_notes":  cheat_sheet,
    }


# ════════════════════════════════════════════════════════════════════════════════
#  FLASK ROUTES
# ════════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/summarize", methods=["POST"])
def summarize():
    """Full structured summary: summary text + key concepts + quiz + exam notes."""
    try:
        uploaded_text = get_uploaded_text(request)
    except ValueError as exc:
        log.warning("Validation error: %s", exc)
        return jsonify({"error": str(exc)}), 400

    log.info("Running summarisation pipeline on %d chars...", len(uploaded_text))

    summary      = extractive_summary(uploaded_text, sentence_count=6)
    key_concepts = extract_keywords(uploaded_text, top_n=10)
    quiz_qs      = generate_quiz(uploaded_text, n=4)
    exam_notes   = generate_exam_notes(uploaded_text)

    words = uploaded_text.split()
    return jsonify({
        "summary":        summary,
        "key_concepts":   key_concepts,
        "quiz_questions": quiz_qs,
        "exam_notes":     exam_notes,
        "word_count":     len(words),
        "reading_time":   max(1, len(words) // 200),
    })


@app.route("/quiz", methods=["POST"])
def quiz():
    """Generate 5–7 quiz questions from the actual uploaded document."""
    try:
        uploaded_text = get_uploaded_text(request)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    log.info("Generating quiz from %d chars...", len(uploaded_text))
    quiz_qs = generate_quiz(uploaded_text, n=7)
    return jsonify({"quiz_questions": quiz_qs})


@app.route("/simplify", methods=["POST"])
def simplify():
    """Rewrite the document in simpler language and extract a glossary."""
    try:
        uploaded_text = get_uploaded_text(request)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    log.info("Simplifying %d chars...", len(uploaded_text))
    simplified, glossary = simplify_text(uploaded_text)
    return jsonify({"simplified": simplified, "glossary": glossary})


@app.route("/exam-mode", methods=["POST"])
def exam_mode():
    """Full exam preparation package from the uploaded document."""
    try:
        uploaded_text = get_uploaded_text(request)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    log.info("Building exam package from %d chars...", len(uploaded_text))
    package = generate_exam_package(uploaded_text)
    return jsonify(package)


# ════════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("LectureMind AI starting — 100%% free, offline, no API key required.")
    app.run(debug=True, port=5000)