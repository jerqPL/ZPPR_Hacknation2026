import secrets
from fastapi import APIRouter, Depends, Header, HTTPException, status
from app.config import settings
from app.models.parameters import LegalParameters
from app.services.parameter_store import parameter_store

router = APIRouter(prefix="/admin", tags=["Panel administracyjny"])


def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    if not x_admin_key or not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak lub nieprawidłowy klucz administratora (nagłówek X-Admin-Key).",
        )


@router.get("/parameters", response_model=LegalParameters)
def get_parameters():
    return parameter_store.get()


@router.put("/parameters", response_model=LegalParameters, dependencies=[Depends(require_admin_key)])
def update_parameters(new_params: LegalParameters):
    return parameter_store.update(new_params)


@router.post("/parameters/reset", response_model=LegalParameters, dependencies=[Depends(require_admin_key)])
def reset_parameters():
    return parameter_store.reset()
