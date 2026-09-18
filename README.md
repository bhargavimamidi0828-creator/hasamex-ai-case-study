# HASAMEX - Expert Call Analysis

## European Robotic Surgery Market

A Flask-based application for analyzing expert interview evidence across France, Germany, and the United Kingdom.

The application presents an interview guide, expert responses, supporting evidence, timestamps, cross-transcript themes, differences between markets, and an evidence search feature.

---

## Project Overview

This project was developed as a technical case study for analyzing expert calls in the European robotic surgery market.

The application organizes interview evidence from three expert perspectives:

- France — Dr. Jean Martin
- Germany — Anna Keller
- United Kingdom — Dr. Emily Carter

Users can select an interview-guide question and review the corresponding expert answers, evidence, timestamps, common themes, and market differences.

The application also provides an **Ask Across All Transcripts** feature that searches the available interview evidence and returns relevant supporting passages.

---

## Features

### 1. Interview Guide

The application contains six interview-guide questions:

1. How would you describe current adoption of robotic surgery in your market?
2. What are the main barriers to adoption?
3. How important are hospital budgets and ROI in purchasing decisions?
4. How important are surgeon training and clinical outcomes?
5. What adoption trend do you expect over the next 3–5 years?
6. What is the typical hospital decision-making timeline for purchasing a new robotic system?

---

### 2. Expert-Level Analysis

For each interview question, the application presents:

- Expert answer
- Supporting evidence
- Timestamp
- Country
- Expert name

The evidence is displayed alongside the corresponding analysis so that users can trace the answer back to the interview evidence.

---

### 3. Cross-Transcript Analysis

The application identifies:

- Common themes across the three markets
- Differences between expert perspectives
- Market-specific considerations

This allows users to compare the interview evidence across France, Germany, and the United Kingdom.

---

### 4. Ask Across All Transcripts

Users can enter a question and search across the available interview evidence.

The search returns relevant evidence together with:

- Country
- Expert
- Interview topic
- Timestamp
- Supporting evidence

The current implementation uses evidence retrieval from the structured interview analysis.

---

## Technology Stack

- Python
- Flask
- HTML
- CSS
- Jinja2
- Regular expressions for evidence search

---

## Project Structure

```text
HASAMEX-AI-CASE/
│
├── data/
│   ├── france.txt
│   ├── germany.txt
│   └── uk.txt
│
├── static/
│
├── templates/
│   └── index.html
│
├── venv/
│
├── app.py
├── README.md
└── requirements.txt
```

---

## How the Application Works

The application follows this flow:

```
Interview Guide
   ↓
Select a Question
   ↓
Expert-Level Analysis
   ↓
Supporting Evidence + Timestamp
   ↓
Cross-Transcript Analysis
   ↓
Ask Across All Transcripts
   ↓
Relevant Interview Evidence
```

---

## Local Setup

### 1. Clone the repository

```
git clone YOUR_GITHUB_REPOSITORY_URL
```

Move into the project directory:

```
cd HASAMEX-AI-CASE
```

---

### 2. Create a virtual environment

Windows:

```
python -m venv venv
```

Activate it:

```
venv\Scripts\activate
```

---

### 3. Install dependencies

```
pip install -r requirements.txt
```

---

### 4. Run the application

```
python app.py
```

The Flask application will start locally.

Open the local URL shown in the terminal, typically:

```
http://127.0.0.1:5000
```

---

## Using the Application

### Interview Guide

Select one of the six interview questions and click **Analyze**.

The application displays the corresponding expert responses for France, Germany, and the United Kingdom.

### Cross-Transcript Analysis

Review the common themes and differences identified across the three expert perspectives.

### Ask Across All Transcripts

Enter a question such as:

```
What are the main barriers to adoption?
```

and select **Search Transcripts**.

The application returns relevant interview evidence from the available analysis.

---

## Evidence and Grounding

The application is designed to keep analytical answers connected to interview evidence.

The evidence displayed in the interface includes the corresponding expert, market, supporting passage, and timestamp where available.

The search functionality currently retrieves relevant evidence from the structured interview analysis rather than generating unsupported claims.

---

## Current AI Status

The current version implements the evidence-analysis and retrieval workflow.

A future AI integration can use the retrieved evidence as the **only context provided to a language model**.

The intended architecture is:

```
User Question
      ↓
Evidence Retrieval
      ↓
Relevant Interview Evidence
      ↓
AI Model
      ↓
Grounded Answer
      ↓
Supporting Evidence + Timestamp
```

The AI layer should only use retrieved interview evidence and should not invent facts, quotes, or timestamps.

---

## Limitations

- The current version does not require an external AI API.
- The Ask feature currently performs evidence retrieval rather than generating a new AI response.
- The timestamp availability depends on the source evidence provided to the application.
- The application is intended as a technical case-study prototype and is not a production research platform.

---

## Future Improvements

Potential improvements include:

- Grounded LLM integration
- Semantic/vector search
- Retrieval-Augmented Generation (RAG)
- Automatic citation of supporting evidence
- More advanced theme detection
- Improved comparison across markets
- Uploading and analyzing additional interview transcripts
- Conversation history for follow-up questions

---

## Security Notes

Do not commit sensitive information such as:

- API keys
- Passwords
- `.env` files containing secrets
- Private credentials
- The Python virtual environment

Use environment variables for future API integrations.

---

## Author

HASAMEX AI Engineer Technical Case Study

Built using Python and Flask.

