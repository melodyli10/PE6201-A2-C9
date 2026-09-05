"""Panel lookup against the insurer's own table. Non-panel doesn't refuse a claim by
itself, but it changes what the decision record must say."""

from src import data_store


def get_hospital_status(hospital_id: str) -> dict:
    hospital = data_store.find_hospital(hospital_id)
    if hospital is None:
        return {"error": f"no hospital found for hospital_id={hospital_id!r}"}
    return {
        "hospital_id": hospital_id,
        "panel": hospital["panel"],
        "name": hospital["name"],
    }
