# 🧠 Smart Lecture Summarizer — LectureMindAI

A full-stack AI-powered web application for students to summarize lecture notes, generate quiz questions, and create exam revision content. Built with Flask (Python) and Claude AI.

---

## 🚀 Quick Setup (5 Steps)

### Step 1 — Clone / Download the Project

```bash
git clone https://github.com/YOUR_USERNAME/smart-lecture-summarizer.git
cd smart-lecture-summarizer
```

Or download and extract the ZIP file.

---

### Step 2 — Create a Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

---

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `flask` — web framework
- `requests` — for Claude API calls
- `pymupdf` — PDF text extraction
- `python-docx` — DOCX text extraction

---

### Step 4 — Run the App

```bash
python app.py
```

You'll see:
```
 * Running on http://127.0.0.1:5000
```

Open your browser and visit: **http://localhost:5000**

---

### Step 5 — Use the App!

1. Click **"Upload Notes"** or **"Paste Text"**
2. Upload a PDF/DOCX/TXT file, or paste lecture content
3. Click **"Summarize with AI"**
4. Get instant: Summary · Key Points · Concepts · Revision Notes
5. Use extra features: Quiz Generator · Exam Mode · Simplify Notes

---

## 📁 Folder Structure

```
smart-lecture-summarizer/
│
├── app.py                  ← Flask backend (main server)
├── requirements.txt        ← Python dependencies
├── README.md               ← This file
│
├── templates/
│   └── index.html          ← Main HTML page
│
├── static/
│   ├── css/
│   │   └── style.css       ← Dark AI theme stylesheet
│   └── js/
│       └── main.js         ← All frontend interactions
│
└── uploads/                ← Uploaded files stored here (auto-created)
```

---

## ⚙️ Flask Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Homepage |
| `/summarize` | POST | Main summarization (file or text) |
| `/quiz` | POST | Generate quiz questions |
| `/simplify` | POST | Simplify notes |
| `/exam-mode` | POST | Exam revision content |

---

## 🎯 Features

| Feature | Description |
|---------|-------------|
| 📄 File Upload | PDF, DOCX, TXT support |
| 🤖 AI Summary | Concise 3-5 sentence summary |
| 📋 Key Points | Top 5 important points extracted |
| 💡 Concepts | Important concept tags |
| 📝 Revision Notes | Quick bullet-point revision notes |
| ❓ Quiz Generator | 5 MCQ questions with answer checking |
| 📖 Simplify Mode | Rewrite in simple beginner language |
| 🎓 Exam Mode | Must-know facts + likely questions |
| ⏱️ Reading Time | Estimated reading time |
| 📋 Copy Summary | One-click copy to clipboard |

---

## 🛠️ Tech Stack

- **Frontend**: HTML5, CSS3 (CSS Variables, Animations), Vanilla JS
- **Backend**: Python 3.10+, Flask
- **AI**: Claude Sonnet API (Anthropic)
- **PDF**: PyMuPDF (fitz)
- **DOCX**: python-docx
- **Icons**: Font Awesome 6
- **Fonts**: Syne + DM Sans (Google Fonts)

---

## 🐛 Troubleshooting

**"ModuleNotFoundError"** → Run `pip install -r requirements.txt` inside the virtual environment

**"Network error"** → Make sure Flask is running (`python app.py`)

**PDF not extracting** → Ensure `pymupdf` is installed: `pip install pymupdf`

**Port already in use** → Change port in `app.py`: `app.run(port=5001)`

---

## 📦 Deployment

### Deploy to Render (Free)
1. Push to GitHub
2. Go to [render.com](https://render.com), create a Web Service
3. Set Build Command: `pip install -r requirements.txt`
4. Set Start Command: `python app.py`

### Deploy to Railway
1. Push to GitHub
2. Connect at [railway.app](https://railway.app)
3. Auto-detected as Python app

---

## 👨‍💻 Built By

**CSE Final Year Student Project**  
Stack: Flask + Claude AI + HTML/CSS/JS  
For: BTech Computer Science & Engineering Portfolio

---

## 📄 License

MIT License — Free to use and modify for educational purposes.