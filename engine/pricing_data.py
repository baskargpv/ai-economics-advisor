import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"

with open(_DATA_DIR / "pricing.json") as f:
    _pricing_data = json.load(f)


def get_all_models():
    return _pricing_data["models"]


def get_model(model_id):
    """Look up a model definition by id. Raises if not found."""
    for m in _pricing_data["models"]:
        if m["id"] == model_id:
            return m
    raise ValueError(f"Unknown model id: {model_id}")
