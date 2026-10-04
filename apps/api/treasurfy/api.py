from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

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
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from treasurfy.schemas import (
    CashPositionResponse,
    ExpectedCashFlowCreate,
    ExpectedCashFlowResponse,
    ForecastRequest,
    ForecastResponse,
    HealthResponse,
    ImportRunResponse,
    PaymentAuditEventResponse,
    PaymentCreate,
    PaymentDecisionRequest,
    PaymentProfileResponse,
    PaymentResponse,
)
from treasurfy.services.access import (
    WorkspaceAccessDeniedError,
    WorkspaceNotFoundError,
)
from treasurfy.services.cash_position import (
    MissingFxRateError,
    get_cash_position,
)
from treasurfy.services.forecast import (
    CashFlowValidationError,
    ForecastConfigurationError,
    add_expected_cash_flow,
    create_forecast,
    list_expected_cash_flows,
)
from treasurfy.services.imports import (
    ImportFileError,
    import_bank_csv,
    list_import_runs,
)
from treasurfy.services.payments import (
    PaymentNotFoundError,
    PaymentStateError,
    PaymentValidationError,
    create_payment,
    decide_payment,
    export_iso20022,
    list_payment_audit_events,
    list_payment_profiles,
    list_payments,
    submit_payment,
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


@router.post(
    "/workspaces/{workspace_id}/forecasts",
    response_model=ForecastResponse,
)
def run_forecast(
    workspace_id: str,
    request: ForecastRequest,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> ForecastResponse:
    try:
        return create_forecast(
            session,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            as_of_date=request.as_of_date or datetime.now(UTC).date(),
            horizon_days=request.horizon_days,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Workspace not found.") from error
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(
            status_code=403, detail="User does not belong to this workspace."
        ) from error
    except ForecastConfigurationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get(
    "/workspaces/{workspace_id}/expected-cash-flows",
    response_model=list[ExpectedCashFlowResponse],
)
def expected_cash_flows(
    workspace_id: str,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> list[ExpectedCashFlowResponse]:
    try:
        return list_expected_cash_flows(
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
    except ForecastConfigurationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/workspaces/{workspace_id}/expected-cash-flows",
    response_model=ExpectedCashFlowResponse,
    status_code=201,
)
def create_expected_cash_flow(
    workspace_id: str,
    request: ExpectedCashFlowCreate,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> ExpectedCashFlowResponse:
    try:
        return add_expected_cash_flow(
            session,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            request=request,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Workspace not found.") from error
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to create cash flows for this workspace.",
        ) from error
    except (CashFlowValidationError, ForecastConfigurationError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get(
    "/workspaces/{workspace_id}/payment-profiles",
    response_model=list[PaymentProfileResponse],
)
def payment_profiles(
    workspace_id: str,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> list[PaymentProfileResponse]:
    try:
        return list_payment_profiles(
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


@router.get(
    "/workspaces/{workspace_id}/payments",
    response_model=list[PaymentResponse],
)
def payments(
    workspace_id: str,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> list[PaymentResponse]:
    try:
        return list_payments(
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


@router.post(
    "/workspaces/{workspace_id}/payments",
    response_model=PaymentResponse,
    status_code=201,
)
def prepare_payment(
    workspace_id: str,
    request: PaymentCreate,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> PaymentResponse:
    try:
        return create_payment(
            session,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            request=request,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Workspace not found.") from error
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to prepare payments for this workspace.",
        ) from error
    except PaymentValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post(
    "/workspaces/{workspace_id}/payments/{payment_id}/submit",
    response_model=PaymentResponse,
)
def submit_prepared_payment(
    workspace_id: str,
    payment_id: str,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> PaymentResponse:
    try:
        return submit_payment(
            session,
            workspace_id=workspace_id,
            payment_id=payment_id,
            actor_user_id=actor_user_id,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Workspace not found.") from error
    except PaymentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Payment not found.") from error
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(status_code=403, detail="Payment submission is not allowed.") from error
    except (PaymentStateError, PaymentValidationError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _decide_prepared_payment(
    *,
    workspace_id: str,
    payment_id: str,
    request: PaymentDecisionRequest,
    actor_user_id: str,
    session: Session,
    decision: str,
) -> PaymentResponse:
    try:
        return decide_payment(
            session,
            workspace_id=workspace_id,
            payment_id=payment_id,
            actor_user_id=actor_user_id,
            decision=decision,
            comment=request.comment,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Workspace not found.") from error
    except PaymentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Payment not found.") from error
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(status_code=403, detail="Payment approval is not allowed.") from error
    except PaymentStateError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/workspaces/{workspace_id}/payments/{payment_id}/approve",
    response_model=PaymentResponse,
)
def approve_payment(
    workspace_id: str,
    payment_id: str,
    request: PaymentDecisionRequest,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> PaymentResponse:
    return _decide_prepared_payment(
        workspace_id=workspace_id,
        payment_id=payment_id,
        request=request,
        actor_user_id=actor_user_id,
        session=session,
        decision="approved",
    )


@router.post(
    "/workspaces/{workspace_id}/payments/{payment_id}/reject",
    response_model=PaymentResponse,
)
def reject_payment(
    workspace_id: str,
    payment_id: str,
    request: PaymentDecisionRequest,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> PaymentResponse:
    return _decide_prepared_payment(
        workspace_id=workspace_id,
        payment_id=payment_id,
        request=request,
        actor_user_id=actor_user_id,
        session=session,
        decision="rejected",
    )


@router.get(
    "/workspaces/{workspace_id}/payments/{payment_id}/audit-events",
    response_model=list[PaymentAuditEventResponse],
)
def payment_audit_events(
    workspace_id: str,
    payment_id: str,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> list[PaymentAuditEventResponse]:
    try:
        return list_payment_audit_events(
            session,
            workspace_id=workspace_id,
            payment_id=payment_id,
            actor_user_id=actor_user_id,
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Workspace not found.") from error
    except PaymentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Payment not found.") from error
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(
            status_code=403, detail="Payment audit history is not available."
        ) from error


@router.get("/workspaces/{workspace_id}/payments/{payment_id}/iso20022")
def payment_iso20022(
    workspace_id: str,
    payment_id: str,
    actor_user_id: str = Depends(get_actor_user_id),
    session: Session = Depends(get_session),
) -> Response:
    try:
        content, digest = export_iso20022(
            session,
            workspace_id=workspace_id,
            payment_id=payment_id,
            actor_user_id=actor_user_id,
        )
        return Response(
            content=content,
            media_type="application/xml",
            headers={
                "Content-Disposition": f'attachment; filename="payment-{payment_id}.xml"',
                "X-Content-SHA256": digest,
            },
        )
    except WorkspaceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Workspace not found.") from error
    except PaymentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Payment not found.") from error
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(status_code=403, detail="Payment export is not allowed.") from error
    except (PaymentStateError, PaymentValidationError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
