from fastapi import FastAPI
from pydantic import BaseModel
from db.neo4j import get_session
from bkt.pipeline import process_submission_bkt

app = FastAPI(title="SapioCode Cognitive Engine")

# -----------------------------
# Request schema
# -----------------------------
class SubmissionPayload(BaseModel):
    sid: str
    sub_id: str
    correct: bool
    cognitive_state: dict


# -----------------------------
# Submit endpoint
# -----------------------------
@app.post("/submit")
def submit_attempt(payload: SubmissionPayload):
    session = get_session()

    try:
        process_submission_bkt(
            neo4j_session=session,
            sid=payload.sid,
            sub_id=payload.sub_id,
            correct=payload.correct,
            cognitive_state=payload.cognitive_state
        )

        return {
            "status": "success",
            "message": "BKT updated successfully"
        }

    finally:
        session.close()
