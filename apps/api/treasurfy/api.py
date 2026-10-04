from __future__ import annotations

from collections.abc import Iterator

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from treasurfy.schemas import CashPositionResponse, HealthResponse, ImportRunResponse
from treasurfy.services.access import (
    WorkspaceAccessDeniedError,
    WorkspaceNotFoundError,
)
from treasurfy.services.cash_position import (
    MissingFxRateError,
    get_cash_position,
)
from treasurfy.services.imports import (
    ImportFileError,
    import_bank_csv,
    list_import_runs,
)

router = APIRouter(prefix="/api")


def get_session(request: Request) -> Iterator[Session]:
    yield from request.app.state.database.sessions()


def get_actor_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> str:
    if x_user_id is None or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-ID is required for the MVP identity boundary.",
        )
    return x_user_id.strip()


@router.get("/health", response_model=HealthResponse)
def health(session: Session = Depends(get_session)) -> HealthResponse:
    session.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database="ok")


@router.get(
    "/workspaces/{workspace_id}/cash-position",
    response_model=CashPositionResponse,
)
def cash_position(
    workspace_id: str,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> CashPositionResponse:
    try:
        return get_cash_position(
            session,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Workspace not found.") from error
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(
            status_code=403, detail="User does not belong to this workspace."
        ) from error
    except MissingFxRateError as error:
        raise HTTPException(
            status_code=409,
            detail=f"Missing {error.currency} to workspace base-currency FX rate.",
        ) from error


@router.post(
    "/workspaces/{workspace_id}/imports/bank-csv",
    response_model=ImportRunResponse,
)
async def upload_bank_csv(
    workspace_id: str,
    file: UploadFile = File(...),
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> ImportRunResponse:
    content = await file.read()
    try:
        return import_bank_csv(
            session,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            file_name=file.filename or "bank-data.csv",
            content=content,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Workspace not found.") from error
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to import data for this workspace.",
        ) from error
    except ImportFileError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get(
    "/workspaces/{workspace_id}/imports",
    response_model=list[ImportRunResponse],
)
def import_history(
    workspace_id: str,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> list[ImportRunResponse]:
    try:
        return list_import_runs(
            session,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Workspace not found.") from error
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(
            status_code=403, detail="User does not belong to this workspace."
        ) from error
