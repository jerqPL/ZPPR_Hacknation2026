from fastapi import APIRouter
from app.models.parameters import LegalParameters
from app.services.parameter_store import parameter_store

router = APIRouter(prefix="/admin", tags=["Panel administracyjny"])


@router.get("/parameters", response_model=LegalParameters)
def get_parameters():
    return parameter_store.get()


@router.put("/parameters", response_model=LegalParameters)
def update_parameters(new_params: LegalParameters):
    return parameter_store.update(new_params)


@router.post("/parameters/reset", response_model=LegalParameters)
def reset_parameters():
    return parameter_store.reset()
