"""POST /api/analyze and GET /api/directory. Owner: detector."""

from fastapi import APIRouter

from app.detector.analyze import analyze
from app.directory.directory import load_directory, localized
from app.schemas import AnalyzeRequest, AnalyzeResponse, Contact, Language

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_route(req: AnalyzeRequest) -> AnalyzeResponse:
    return await analyze(req)


@router.get("/directory", response_model=list[Contact])
def directory(lang: Language = Language.en) -> list[Contact]:
    return [localized(c, lang) for c in load_directory()]
