# ⚡ SmartScrub

> An AI-powered, fully schema-agnostic data quality analysis tool. Upload **any dataset** in **any format** and get an instant, beautiful quality report with charts, scores, and smart fix suggestions.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Flask](https://img.shields.io/badge/Flask-2.x-green) ![License](https://img.shields.io/badge/License-MIT-purple)

---

## 🚀 Features

- **📂 Universal Format Support** — CSV, TSV, Excel (.xlsx/.xls), JSON, Parquet, ODS, TXT
- **🔍 Comprehensive Analysis** — Missing values, duplicates, outliers, type mismatches, inconsistencies, empty columns
- **📊 Quality Score (0–100)** — Weighted across 5 dimensions: Completeness, Uniqueness, Validity, Consistency, Accuracy
- **📈 Interactive Charts** — Donut, Bar, Heatmap, Radar charts powered by Chart.js
- **🤖 AI Suggestions** — Gemini API powered (with smart rule-based fallback, no key needed)
- **🔧 Auto-Fix + Download** — One-click clean data export as CSV
- **🌙 Stunning Dark UI** — Glassmorphism, animated orbs, gradient text

---

## 🛠️ Setup

### 1. Clone / Navigate to project
```bash
cd "AI-Data-Quality-Checker"
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Add Gemini API Key for AI suggestions
```bash
# Windows PowerShell
$env:GEMINI_API_KEY = "your-key-here"

# Or create a .env file
GEMINI_API_KEY=your-key-here
```
> ℹ️ Without a key, the app uses smart rule-based suggestions — still very useful!

### 4. Run the app
```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 📁 Project Structure

```
AI-Data-Quality-Checker/
├── app.py                        ← Flask server
├── quality_engine/
│   ├── analyzer.py               ← Universal dataset loader + analysis
│   ├── scorer.py                 ← Quality scoring (5 dimensions)
│   ├── fixer.py                  ← Auto-fix engine
│   └── ai_advisor.py             ← Gemini AI + rule-based suggestions
├── static/
│   ├── index.html                ← Upload landing page
│   ├── report.html               ← Results dashboard
│   └── style.css                 ← Dark glassmorphism styles
├── uploads/                      ← Temporary file storage
├── requirements.txt
├── Procfile                      ← For Heroku/Render deployment
└── .gitignore
```

---

## 🌐 Deploy to Render

1. Push to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `gunicorn app:app`
5. (Optional) Add `GEMINI_API_KEY` environment variable

---

## 📊 Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| CSV | `.csv` | Auto-detects delimiter (`,`, `;`, `|`, `\t`) |
| TSV | `.tsv` | Tab-separated |
| Excel | `.xlsx`, `.xls` | All sheets, first by default |
| JSON | `.json` | Array or nested object |
| Parquet | `.parquet` | Apache Parquet |
| ODS | `.ods` | OpenDocument Spreadsheet |
| Text | `.txt` | Auto-detect delimiter |

---

## 🧠 How the Quality Score Works

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Completeness | 30% | Missing values |
| Uniqueness | 20% | Duplicate rows |
| Validity | 20% | Type mismatches, empty columns |
| Consistency | 15% | Format variations |
| Accuracy | 15% | Statistical outliers |

---

## 📄 License

MIT © 2024
