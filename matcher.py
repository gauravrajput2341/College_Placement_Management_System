"""Resume-to-drive matching (simple AI/ML feature).

Two scores are calculated for every drive:
1. Skill match   - what % of the drive's required skills appear in the resume.
2. Text similarity - TF-IDF + cosine similarity between resume text and the
                     drive's skills text (catches related words, not just exact skills).
"""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def split_skills(skills_text):
    """'Python, SQL\nFlask' -> ['python', 'sql', 'flask']"""
    if not skills_text:
        return []
    parts = skills_text.replace("\n", ",").replace(";", ",").split(",")
    return [p.strip().lower() for p in parts if p.strip()]


def skill_in_text(skill, text_lower):
    """True if the skill appears as a whole word/phrase (so 'sql' does not match 'mysqlx')."""
    pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
    return re.search(pattern, text_lower) is not None


def tfidf_similarity(resume_text, skills_texts):
    """Cosine similarity (0 to 1) of the resume with each drive's skills text."""
    zeros = [0.0] * len(skills_texts)
    if not resume_text.strip() or not skills_texts:
        return zeros
    docs = [resume_text] + skills_texts
    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform(docs)
    except ValueError:            # happens if every document is empty
        return zeros
    sims = cosine_similarity(matrix[0:1], matrix[1:])[0]
    return [float(x) for x in sims]


def match_drives(resume_text, drives):
    """Return {drive_id: {...scores...}} for a list of drive rows."""
    resume_text = resume_text or ""
    text_lower = resume_text.lower()
    skills_texts = [(d.get("required_skills") or "") for d in drives]
    sims = tfidf_similarity(resume_text, skills_texts)

    results = {}
    for d, sim in zip(drives, sims):
        skills = split_skills(d.get("required_skills"))
        matched = [s for s in skills if skill_in_text(s, text_lower)]
        missing = [s for s in skills if s not in matched]
        results[d["drive_id"]] = {
            "has_skills": bool(skills),
            "skill_match": round(len(matched) / len(skills) * 100) if skills else 0,
            "matched": matched,
            "missing": missing,
            "similarity": round(sim * 100),
        }
    return results


def match_applicants(skills_text, applicants):
    """Opposite direction: ONE drive, MANY applicants.
    Returns {application_id: {...scores...}} for a list of applicant rows."""
    skills = split_skills(skills_text)
    docs = [(a.get("resume_text") or "") for a in applicants]

    sims = [0.0] * len(docs)
    if skills and any(d.strip() for d in docs):
        try:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            matrix = vectorizer.fit_transform([skills_text] + docs)
            sims = [float(x) for x in cosine_similarity(matrix[0:1], matrix[1:])[0]]
        except ValueError:
            pass

    results = {}
    for a, doc, sim in zip(applicants, docs, sims):
        text_lower = doc.lower()
        matched = [s for s in skills if skill_in_text(s, text_lower)]
        missing = [s for s in skills if s not in matched]
        results[a["application_id"]] = {
            "has_skills": bool(skills),
            "has_resume": bool(doc.strip()),
            "skill_match": round(len(matched) / len(skills) * 100) if skills else 0,
            "matched": matched,
            "missing": missing,
            "similarity": round(sim * 100),
        }
    return results


# Run this file directly to test:  python matcher.py
if __name__ == "__main__":
    resume = ("Rahul Kumar B.Tech AI/ML. Skills: Python, SQL, Machine Learning, Flask. "
              "Built a placement management system using Flask and MySQL.")
    drives = [
        {"drive_id": 1, "required_skills": "python, sql, machine learning, flask"},
        {"drive_id": 2, "required_skills": "java, spring boot, microservices"},
        {"drive_id": 3, "required_skills": "python, tensorflow, deep learning"},
        {"drive_id": 4, "required_skills": None},
    ]
    for drive_id, r in match_drives(resume, drives).items():
        print(drive_id, r)

    print("--- one drive, many applicants ---")
    applicants = [
        {"application_id": 10, "resume_text": resume},
        {"application_id": 11, "resume_text": "Java Spring Boot developer"},
        {"application_id": 12, "resume_text": ""},
    ]
    for app_id, r in match_applicants("python, sql, machine learning, flask", applicants).items():
        print(app_id, r)