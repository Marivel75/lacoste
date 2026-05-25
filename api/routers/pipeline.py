from fastapi import APIRouter, HTTPException

from api.schemas.pipeline import CollectRequest, CollectResult
from src.config import Config
from src.pipeline.pipeline import VeillePipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/collect", response_model=CollectResult)
def trigger_collect(req: CollectRequest = CollectRequest()):
    try:
        config = Config.load()
        config.lookback_days = req.days
        config.min_score = req.min_score
        result = VeillePipeline(config).run()
        return CollectResult(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
