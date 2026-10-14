from fastapi import APIRouter
from pydantic import BaseModel, Field

from nlp.pipeline import analyze_text


router = APIRouter(prefix="/nlp", tags=["NLP"])


class NLPAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1)


@router.post("/analyze")
def analyze(request: NLPAnalyzeRequest):
    return analyze_text(request.text)