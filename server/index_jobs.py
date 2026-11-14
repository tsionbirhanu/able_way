"""Index data/jobs.json into server/data/chunks_jobs.json for the Tutor RAG engine."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAVANNA = HERE.parent
JOBS_PATH = SAVANNA / "data" / "jobs.json"
OUT_PATH = HERE / "data" / "chunks_jobs.json"

def index_jobs():
    if not JOBS_PATH.exists():
        print(f"Warning: {JOBS_PATH} not found.")
        return
    jobs = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    chunks = []
    for j in jobs:
        # English chunk
        chunks.append({
            "id": f"job-{j['id']}-en",
            "corpus": "jobs",
            "kind": "job",
            "lang": "en",
            "course": "Career Gateway: Accessible Jobs",
            "title": f"{j['title']} ({j['company']})",
            "page": "jobs.html",
            "url": "pages/jobs.html",
            "text": (
                f"Job Title: {j['title']}\n"
                f"Company: {j['company']}\n"
                f"Location: {j['location']}\n"
                f"Remote: {'Yes' if j.get('remote') else 'No'}\n"
                f"Required Skills: {', '.join(j.get('skills', []))}\n"
                f"Deadline: {j.get('deadline', '')}\n"
                f"Description: {j.get('description', {}).get('en', '')}\n"
                f"Application Link: {j.get('link', '')}"
            )
        })
        # Amharic chunk
        chunks.append({
            "id": f"job-{j['id']}-am",
            "corpus": "jobs",
            "kind": "job",
            "lang": "am",
            "course": "የሥራ ዕድሎች (Career Gateway)",
            "title": f"{j['title']} ({j['company']})",
            "page": "jobs.html",
            "url": "pages/jobs.html",
            "text": (
                f"የሥራ መደብ: {j['title']}\n"
                f"ድርጅት: {j['company']}\n"
                f"ቦታ: {j['location']}\n"
                f"የርቀት ሥራ: {'አዎ' if j.get('remote') else 'አይደለም'}\n"
                f"የሚያስፈልጉ ክህሎቶች: {', '.join(j.get('skills', []))}\n"
                f"የማመልከቻ ጊዜ ገደብ: {j.get('deadline', '')}\n"
                f"ዝርዝር መግለጫ: {j.get('description', {}).get('am', '')}\n"
                f"የማመልከቻ ማስፈንጠሪያ: {j.get('link', '')}"
            )
        })
    OUT_PATH.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(chunks)} job chunks in {OUT_PATH.name}")

if __name__ == "__main__":
    index_jobs()
