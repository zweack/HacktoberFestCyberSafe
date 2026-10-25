"""Fault switches stored in the shared DB so the API and worker both see them."""

from app import db
from app.schemas import ChaosSettings

_KEY = "chaos"


def get_chaos() -> ChaosSettings:
    return ChaosSettings.model_validate(db.get_json(_KEY, ChaosSettings().model_dump()))


def set_chaos(settings: ChaosSettings) -> ChaosSettings:
    db.put_json(_KEY, settings.model_dump())
    return settings
