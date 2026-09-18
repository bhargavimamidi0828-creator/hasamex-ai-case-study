from flask import Flask, render_template, request
import os
import re
import json
import urllib.error
import urllib.request

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

questions = [
    "How would you describe current adoption of robotic surgery in your market?",
    "What are the main barriers to adoption?",
    "How important are hospital budgets and ROI in purchasing decisions?",
    "How important are surgeon training and clinical outcomes?",
    "What adoption trend do you expect over the next 3–5 years?",
    "What is the typical hospital decision-making timeline for purchasing a new robotic system?"
]


def normalize_text(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def load_transcript(country):
    file_path = os.path.join(DATA_DIR, f"{country.lower()}.txt")
    with open(file_path, "r", encoding="utf-8") as file:
        raw_text = file.read().strip()

    sections = [section.strip() for section in re.split(r"\n\s*\n+", raw_text) if section.strip()]
    expert = sections[0] if sections else country
    segments = sections[1:] if len(sections) > 1 else sections

    return {
        "country": country,
        "expert": expert,
        "segments": segments,
    }


transcripts = {
    "France": load_transcript("France"),
    "Germany": load_transcript("Germany"),
    "UK": load_transcript("UK"),
}


TOPIC_RULES = {
    "adoption": {
        "keywords": ["adoption", "market", "access", "hospitals", "increasing", "growing", "uneven", "standard"],
    },
    "barriers": {
        "keywords": ["barrier", "barriers", "capital", "cost", "financial", "funding", "approval", "economic", "utilisation", "roi"],
    },
    "budget_roi": {
        "keywords": ["budget", "roi", "return on investment", "finance", "cost", "procurement", "maintenance", "pay for itself", "economic case"],
    },
    "training_outcomes": {
        "keywords": ["training", "surgeon", "clinical", "outcomes", "patient", "outcome", "utilisation", "operational"],
    },
    "growth": {
        "keywords": ["growth", "trend", "increase", "annual", "expect", "future", "double", "single"],
    },
    "timeline": {
        "keywords": ["timeline", "months", "purchase", "procurement", "budget cycle", "implementation", "how long"],
    },
}


def classify_question(question):
    if not question:
        return "general"

    text = normalize_text(question)

    if any(term in text for term in ["purchase timeline", "timeline", "how long", "months", "implementation", "decision-making timeline", "procurement time"]):
        return "timeline"
    if any(term in text for term in ["barrier", "barriers", "main challenge", "challenging", "obstacle", "obstacles"]):
        return "barriers"
    if any(term in text for term in ["budget", "roi", "return on investment", "financial", "purchase decision", "funding", "cost", "economic"]):
        return "budget_roi"
    if any(term in text for term in ["training", "surgeon", "clinical outcome", "clinical outcomes", "patient outcome", "patient outcomes"]):
        return "training_outcomes"
    if any(term in text for term in ["adoption", "market", "access", "current adoption", "how would you describe"]):
        return "adoption"
    if any(term in text for term in ["growth", "trend", "future", "expect", "over the next", "annual"]):
        return "growth"

    return "general"


def retrieve_relevant_segments(question, limit=3):
    if not question:
        return []

    question_text = normalize_text(question)
    topic = classify_question(question)
    matches = []

    for country, data in transcripts.items():
        for segment in data["segments"]:
            segment_text = normalize_text(segment)
            score = 0

            # direct token overlap
            for token in set(question_text.split()):
                if token and token in segment_text:
                    score += 2

            # topic-specific signal
            topic_keywords = TOPIC_RULES.get(topic, {}).get("keywords", [])
            for keyword in topic_keywords:
                if keyword in segment_text:
                    score += 4

            # strong semantic matches for actual barrier/timeline questions
            if topic == "barriers":
                if any(word in segment_text for word in ["barrier", "capital", "cost", "funding", "budget", "approval", "economic", "utilisation"]):
                    score += 6
            if topic == "timeline":
                if any(word in segment_text for word in ["months", "timeline", "purchase", "procurement", "budget cycle", "implementation"]):
                    score += 6
            if topic == "budget_roi":
                if any(word in segment_text for word in ["budget", "roi", "finance", "cost", "maintenance", "economic case", "pay for itself"]):
                    score += 6
            if topic == "training_outcomes":
                if any(word in segment_text for word in ["training", "surgeon", "clinical", "outcomes", "patient", "operational"]):
                    score += 6
            if topic == "adoption":
                if any(word in segment_text for word in ["adoption", "increasing", "growing", "access", "hospitals", "standard"]):
                    score += 6
            if topic == "growth":
                if any(word in segment_text for word in ["growth", "increasing", "expect", "annual", "future", "gradual"]):
                    score += 6

            if score > 0:
                matches.append({
                    "country": country,
                    "expert": data["expert"],
                    "text": segment,
                    "score": score,
                    "timestamp": None,
                })

    matches.sort(key=lambda item: (-item["score"], item["country"]))
    return matches[:limit]


def build_grounded_summary(question, matches):
    if not matches:
        return "I could not find direct evidence in the transcripts for that question. Try asking about adoption, budgets, barriers, training, growth, or purchase timelines."

    excerpts = []
    seen = set()
    for match in matches[:3]:
        text = match.get("text", "").strip()
        if not text:
            continue
        text = text.replace("\n", " ")
        if text not in seen:
            seen.add(text)
            excerpts.append(text)

    if not excerpts:
        return "I found the relevant question area, but there was no grounded transcript text to summarize."

    summary = " ".join(excerpts)
    if len(summary) > 700:
        summary = summary[:697].rsplit(" ", 1)[0] + "..."

    return f"Based on the matched transcript evidence, the strongest points are: {summary}"


def generate_ai_answer(question, matches):
    if not question or not matches:
        return build_grounded_summary(question, matches)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return build_grounded_summary(question, matches)

    evidence_block = "\n\n".join(
        f"[{item['country']}] {item['expert']}: {item['text']}" for item in matches
    )

    prompt = (
        "You are answering a medical-market-analysis question using only the transcript evidence provided below. "
        "Do not invent details. Do not answer from outside knowledge. Use only the facts in the provided excerpts. "
        "If the evidence is limited, say so clearly. Keep the answer concise and grounded in the transcript content.\n\n"
        f"Question: {question}\n\nEvidence:\n{evidence_block}"
    )

    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "Use only the evidence provided in the transcript excerpts. Do not invent timestamps or facts."},
            {"role": "user", "content": prompt},
        ],
    }

    try:
        request = urllib.request.Request(
            url="https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
        return build_grounded_summary(question, matches)


analysis = {
    questions[0]: {
        "France": {
            "expert": "Dr. Jean Martin",
            "answer": "Adoption is growing, but it remains concentrated in larger academic hospitals and private centres with stronger capital budgets.",
            "evidence": [
                {
                    "quote": "Adoption is growing, but it is still concentrated in larger academic hospitals and private centres with stronger capital budgets. Smaller regional hospitals are much slower.",
                    "timestamp": "00:18"
                }
            ]
        },
        "Germany": {
            "expert": "Anna Keller",
            "answer": "Adoption is growing but uneven, with large university hospitals more advanced than smaller hospitals.",
            "evidence": [
                {
                    "quote": "It is growing, but adoption is quite uneven. Large university hospitals are much more advanced, while many smaller hospitals are still waiting.",
                    "timestamp": "00:16"
                }
            ]
        },
        "UK": {
            "expert": "Dr. Emily Carter",
            "answer": "Adoption is increasing, with robotic surgery becoming standard for selected procedures in some larger NHS trusts, although access varies.",
            "evidence": [
                {
                    "quote": "Adoption is increasing, and in some larger NHS trusts robotic surgery is becoming standard for selected procedures. But access still varies significantly by hospital.",
                    "timestamp": "00:14"
                }
            ]
        },
        "common": [
            "All three experts describe robotic surgery adoption as increasing.",
            "Larger or more advanced hospitals are further ahead.",
            "Access and adoption remain uneven across hospitals."
        ],
        "differences": [
            "France highlights larger academic hospitals and private centres with stronger capital budgets.",
            "Germany highlights the gap between large university hospitals and smaller hospitals.",
            "The UK highlights selected procedures in larger NHS trusts and variation in access."
        ]
    },
    questions[1]: {
        "France": {
            "expert": "Dr. Jean Martin",
            "answer": "Capital budget approval and the need for a strong economic case are major barriers.",
            "evidence": [
                {
                    "quote": "The biggest issue is still capital budget approval. Hospitals may like the technology clinically, but purchasing committees need a strong economic case before approving a system.",
                    "timestamp": "01:20"
                }
            ]
        },
        "Germany": {
            "expert": "Anna Keller",
            "answer": "Cost and proving sufficient utilisation are the main barriers.",
            "evidence": [
                {
                    "quote": "Cost is the first barrier. These are large capital purchases, and hospital finances are under pressure. The second issue is proving that the system will be used enough.",
                    "timestamp": "01:10"
                }
            ]
        },
        "UK": {
            "expert": "Dr. Emily Carter",
            "answer": "Funding and training capacity are both important barriers to adoption.",
            "evidence": [
                {
                    "quote": "Funding is important, but I would say training capacity is just as important. You can buy a system, but if you cannot train enough surgeons and theatre staff, adoption stalls.",
                    "timestamp": "01:05"
                }
            ]
        },
        "common": [
            "Financial considerations are important barriers across the markets.",
            "Hospitals need sufficient utilisation to make the investment sustainable.",
            "Operational readiness, including training, affects adoption."
        ],
        "differences": [
            "France emphasizes capital budget approval and the economic case.",
            "Germany emphasizes cost, hospital finances and proving sufficient utilisation.",
            "The UK gives particular emphasis to training capacity alongside funding."
        ]
    },
    questions[2]: {
        "France": {
            "expert": "Dr. Jean Martin",
            "answer": "ROI is very important. Finance teams examine utilisation, procedure volume, maintenance cost and whether the system will pay for itself.",
            "evidence": [
                {
                    "quote": "Very important. The clinical argument may get surgeons interested, but the finance team wants to understand utilisation, procedure volume, maintenance cost and whether the system will actually pay for itself.",
                    "timestamp": "02:18"
                }
            ]
        },
        "Germany": {
            "expert": "Anna Keller",
            "answer": "The economic case is central to procurement, including total cost of ownership, procedure volume, maintenance and service contracts.",
            "evidence": [
                {
                    "quote": "We look at total cost of ownership, expected procedure volume, maintenance, service contracts and training requirements. A strong clinical case helps, but the economic case decides whether it gets approved.",
                    "timestamp": "02:08"
                }
            ]
        },
        "UK": {
            "expert": "Dr. Emily Carter",
            "answer": "ROI matters, but purchasing decisions also consider clinical and strategic factors rather than being purely financial.",
            "evidence": [
                {
                    "quote": "It matters, but the discussion is not always purely financial. Hospitals also consider patient outcomes, length of stay, surgeon recruitment and whether the technology improves their clinical position.",
                    "timestamp": "02:07"
                },
                {
                    "quote": "I would say economics and clinical strategy are balanced. I would not say finance alone decides the purchase.",
                    "timestamp": "03:10"
                }
            ]
        },
        "common": [
            "Economics and financial justification influence purchasing decisions.",
            "Hospitals consider utilisation and expected procedure volume.",
            "A strong clinical case alone does not remove the need for economic justification."
        ],
        "differences": [
            "France focuses strongly on ROI, utilisation and whether the system pays for itself.",
            "Germany focuses on total cost of ownership and procurement economics.",
            "The UK describes economics as balanced with clinical strategy and outcomes."
        ]
    },
    questions[3]: {
        "France": {
            "expert": "Dr. Jean Martin",
            "answer": "Training is important for achieving sufficient utilisation, while clinical outcomes are necessary but not sufficient on their own.",
            "evidence": [
                {
                    "quote": "Training matters, especially in the first year. If only one surgeon can use the system, the economics become difficult. Hospitals want several surgeons trained so utilisation is high enough.",
                    "timestamp": "03:10"
                },
                {
                    "quote": "Clinical outcomes are necessary, but they are not enough on their own.",
                    "timestamp": "04:08"
                }
            ]
        },
        "Germany": {
            "expert": "Anna Keller",
            "answer": "Training is very important operationally because limited surgeon capability can lead to poor utilisation and weaken the business case.",
            "evidence": [
                {
                    "quote": "Very important operationally. If the hospital buys a system but only one surgeon is comfortable using it, utilisation will be poor. That weakens the business case.",
                    "timestamp": "03:05"
                }
            ]
        },
        "UK": {
            "expert": "Dr. Emily Carter",
            "answer": "Training capacity is a major implementation factor, while hospitals also consider patient outcomes and other clinical factors.",
            "evidence": [
                {
                    "quote": "Funding is important, but I would say training capacity is just as important. You can buy a system, but if you cannot train enough surgeons and theatre staff, adoption stalls.",
                    "timestamp": "01:05"
                },
                {
                    "quote": "It matters, but the discussion is not always purely financial. Hospitals also consider patient outcomes, length of stay, surgeon recruitment and whether the technology improves their clinical position.",
                    "timestamp": "02:07"
                }
            ]
        },
        "common": [
            "Training is important for successful implementation and utilisation.",
            "Hospitals need enough trained staff to make effective use of a system.",
            "Clinical considerations also contribute to purchasing decisions."
        ],
        "differences": [
            "France connects training directly to utilisation and economic performance.",
            "Germany emphasizes training as an operational requirement that affects the business case.",
            "The UK emphasizes training capacity alongside funding and clinical considerations."
        ]
    },
    questions[4]: {
        "France": {
            "expert": "Dr. Jean Martin",
            "answer": "Adoption is expected to continue increasing steadily, with stronger centres potentially seeing 15–20% annual procedure growth.",
            "evidence": [
                {
                    "quote": "I expect adoption to continue increasing, probably steadily rather than explosively. I would expect maybe 15 to 20 percent more procedures annually in some of the stronger centres, but smaller hospitals will remain slower.",
                    "timestamp": "05:07"
                }
            ]
        },
        "Germany": {
            "expert": "Anna Keller",
            "answer": "Growth is expected to continue gradually, with procedure-volume growth closer to high single digits or low double digits.",
            "evidence": [
                {
                    "quote": "I would expect continued growth, but probably closer to high single digits or low double digits in procedure volumes rather than something like 20 percent across the whole market.",
                    "timestamp": "05:08"
                }
            ]
        },
        "UK": {
            "expert": "Dr. Emily Carter",
            "answer": "The outlook is positive, and procedure growth above 15% annually could occur in some areas if training expands and systems become more cost competitive.",
            "evidence": [
                {
                    "quote": "I am quite positive. I think adoption could accelerate if training expands and systems become more cost competitive. I could see procedure growth above 15 percent annually in some areas.",
                    "timestamp": "04:06"
                }
            ]
        },
        "common": [
            "All three experts expect adoption to continue growing.",
            "The experts do not describe an immediate universal market-wide surge.",
            "Training and economic factors are connected to future growth."
        ],
        "differences": [
            "France gives an estimate of 15–20% annual procedure growth in some stronger centres.",
            "Germany expects high-single-digit or low-double-digit procedure-volume growth.",
            "The UK describes a positive outlook and possible growth above 15% annually in some areas."
        ]
    },
    questions[5]: {
        "France": {
            "expert": "Dr. Jean Martin",
            "answer": "A typical purchase decision takes around 6–12 months once the hospital becomes serious, although budget-cycle delays can extend the process.",
            "evidence": [
                {
                    "quote": "Six to twelve months is realistic once the hospital becomes serious. It can be longer if the capital committee pushes the purchase into the next budget cycle.",
                    "timestamp": "06:08"
                }
            ]
        },
        "Germany": {
            "expert": "Anna Keller",
            "answer": "Nine to eighteen months is common because procurement, clinical leadership, finance and management need to align.",
            "evidence": [
                {
                    "quote": "Nine to eighteen months is common. Procurement, clinical leadership, finance and management all need to align, so it can move slowly.",
                    "timestamp": "06:05"
                }
            ]
        },
        "UK": {
            "expert": "Dr. Emily Carter",
            "answer": "Around 6–9 months can happen when funding is already available, while waiting for a new capital cycle can take much longer.",
            "evidence": [
                {
                    "quote": "Around six to nine months can happen if funding is already available. If the trust has to wait for a new capital cycle, it can take much longer.",
                    "timestamp": "05:04"
                }
            ]
        },
        "common": [
            "Purchase timelines are measured in months rather than weeks.",
            "Funding and capital-budget timing can affect the process.",
            "Multiple hospital stakeholders can influence the timeline."
        ],
        "differences": [
            "France gives a typical range of 6–12 months.",
            "Germany gives a longer typical range of 9–18 months.",
            "The UK gives around 6–9 months when funding is already available, with longer delays possible around capital cycles."
        ]
    }
}


# -----------------------------
# Transcript Search
# -----------------------------

TRANSCRIPTS = [
    {
        "country": "France",
        "expert": "Dr. Jean Martin",
        "file": "france.txt"
    },
    {
        "country": "Germany",
        "expert": "Anna Keller",
        "file": "germany.txt"
    },
    {
        "country": "United Kingdom",
        "expert": "Dr. Emily Carter",
        "file": "uk.txt"
    }
]

STOPWORDS = {
    "what", "are", "the", "is", "a", "an", "of", "to",
    "in", "on", "for", "how", "would", "you", "describe",
    "and", "or", "do", "does", "this", "that", "with",
    "from", "over", "next", "their", "your", "all"
}


def load_transcript(country, expert, filename):
    """
    Reads one transcript from the data folder
    and separates timestamped sections.
    """

    path = os.path.join(
        os.path.dirname(__file__),
        "data",
        filename
    )

    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as file:
        text = file.read()

    pattern = re.compile(r"\b\d{1,2}:\d{2}\b")
    matches = list(pattern.finditer(text))

    chunks = []

    if not matches:
        if text.strip():
            chunks.append({
                "country": country,
                "expert": expert,
                "timestamp": "Timestamp not detected",
                "text": text.strip()
            })

        return chunks

    for i, match in enumerate(matches):
        timestamp = match.group()
        start = match.end()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        section_text = text[start:end].strip()

        if section_text:
            chunks.append({
                "country": country,
                "expert": expert,
                "timestamp": timestamp,
                "text": section_text
            })

    return chunks


def search_transcripts(query):
    """
    Searches all three transcript files and returns
    the most relevant transcript sections.
    """

    query_words = re.findall(r"[a-zA-Z0-9]+", query.lower())
    query_words = [
        word for word in query_words
        if word not in STOPWORDS and len(word) > 2
    ]

    if not query_words:
        return []

    results = []

    for transcript in TRANSCRIPTS:

        chunks = load_transcript(
            transcript["country"],
            transcript["expert"],
            transcript["file"]
        )

        for chunk in chunks:
            text_lower = chunk["text"].lower()
            score = 0

            for word in query_words:
                if word in text_lower:
                    score += 1

            if score > 0:
                results.append({
                    "country": chunk["country"],
                    "expert": chunk["expert"],
                    "timestamp": chunk["timestamp"],
                    "text": chunk["text"],
                    "score": score
                })

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results[:6]


# ---------------------------------------
# Ask Across All Transcripts
# ---------------------------------------

STOPWORDS = {
    "what", "are", "the", "is", "a", "an", "of", "to",
    "in", "on", "for", "how", "would", "you", "describe",
    "and", "or", "do", "does", "this", "that", "with",
    "from", "over", "next", "their", "your", "all",
    "about", "can", "could", "should", "would"
}

def get_search_words(query):
    words = re.findall(r"[a-zA-Z0-9]+", query.lower())

    return [
        word
        for word in words
        if word not in STOPWORDS and len(word) > 2
    ]

def build_search_index():
    """
    Extracts evidence, timestamps, country and expert
    information from the existing analysis mapping.
    """

    index = []

    def walk(data, question="", country="", expert=""):

        if isinstance(data, dict):

            current_question = question
            current_country = country
            current_expert = expert

            for key, value in data.items():

                key_text = str(key)

                # Detect interview question
                if key_text in questions:
                    current_question = key_text

                # Detect country
                if key_text.lower() in {
                    "france",
                    "germany",
                    "united kingdom",
                    "uk"
                }:
                    current_country = key_text

                # Detect expert
                if key_text.lower() in {
                    "expert",
                    "name"
                } and isinstance(value, str):
                    current_expert = value

                # Evidence found
                if key_text.lower() == "evidence":

                    if isinstance(value, str):

                        timestamp = data.get(
                            "timestamp",
                            data.get("time", "Timestamp not available")
                        )

                        index.append({
                            "question": current_question,
                            "country": current_country,
                            "expert": current_expert,
                            "evidence": value,
                            "timestamp": timestamp
                        })

                walk(
                    value,
                    current_question,
                    current_country,
                    current_expert
                )

        elif isinstance(data, list):

            for item in data:
                walk(
                    item,
                    question,
                    country,
                    expert
                )

    walk(analysis)

    return index

def search_analysis(query):
    """
    Searches all interview evidence and returns
    the most relevant supporting evidence.
    """

    search_words = get_search_words(query)

    if not search_words:
        return []

    index = build_search_index()

    results = []

    for item in index:

        searchable_text = (
            (item.get("question") or "") + " " +
            (item.get("country") or "") + " " +
            (item.get("expert") or "") + " " +
            (item.get("evidence") or "")
        ).lower()

        score = 0

        for word in search_words:

            if word in searchable_text:
                score += 1

        if score > 0:

            result = item.copy()
            result["score"] = score

            results.append(result)

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results[:6]


@app.route("/")
def home():

    selected_question = request.args.get(
        "question",
        ""
    )

    ask_query = request.args.get(
        "ask",
        ""
    ).strip()

    ask_results = []

    if ask_query:
        ask_results = search_analysis(ask_query)

    selected_analysis = None

    if selected_question:
        selected_analysis = analysis.get(
            selected_question
        )

    return render_template(
        "index.html",
        questions=questions,
        selected_question=selected_question,
        analysis=selected_analysis,
        ask_query=ask_query,
        ask_results=ask_results
    )


if __name__ == "__main__":
    app.run(debug=True)
