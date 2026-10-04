from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.orm import Session

from treasurfy.models import (
    AuditEvent,
    BankAccount,
    Entity,
    MembershipRole,
    Payment,
    PaymentDecision,
    PaymentExport,
    PaymentProfile,
    User,
)
from treasurfy.schemas import (
    PaymentAuditEventResponse,
    PaymentCreate,
    PaymentProfileResponse,
    PaymentResponse,
)
from treasurfy.services.access import require_workspace_access


class PaymentNotFoundError(Exception):
    pass


class PaymentStateError(Exception):
    pass


class PaymentValidationError(Exception):
    pass


PREPARATION_ROLES = {MembershipRole.ADMIN, MembershipRole.PREPARER}
APPROVAL_ROLES = {MembershipRole.ADMIN, MembershipRole.APPROVER}
PAYMENT_ROLES = {
    MembershipRole.ADMIN,
    MembershipRole.PREPARER,
    MembershipRole.APPROVER,
    MembershipRole.VIEWER,
}


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def _audit(
    session: Session,
    *,
    payment: Payment,
    actor_user_id: str,
    action: str,
    detail: dict[str, object],
    now: datetime,
) -> None:
    session.add(
        AuditEvent(
            id=str(uuid4()),
            workspace_id=payment.workspace_id,
            actor_user_id=actor_user_id,
            action=action,
            target_type="payment",
            target_id=payment.id,
            detail=json.dumps(detail, sort_keys=True),
            created_at=now,
        )
    )


def _get_payment(session: Session, *, workspace_id: str, payment_id: str) -> Payment:
    payment = session.scalar(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.workspace_id == workspace_id,
        )
    )
    if payment is None:
        raise PaymentNotFoundError
    return payment


def _get_profile(
    session: Session, *, workspace_id: str, profile_id: str
) -> PaymentProfile:
    profile = session.scalar(
        select(PaymentProfile).where(
            PaymentProfile.id == profile_id,
            PaymentProfile.workspace_id == workspace_id,
        )
    )
    if profile is None:
        raise PaymentValidationError("Payment profile was not found in this workspace.")
    return profile


def _validation_errors(
    payment: Payment,
    *,
    profile: PaymentProfile,
    account: BankAccount | None,
    entity: Entity | None,
    today: date,
) -> list[str]:
    errors: list[str] = []
    allowed_currencies = profile.allowed_currencies.split(",")
    account_identifier = re.sub(r"\s+", "", payment.beneficiary_account).upper()

    if entity is None or entity.workspace_id != payment.workspace_id:
        errors.append("Entity does not belong to this workspace.")
    if account is None or account.workspace_id != payment.workspace_id:
        errors.append("Source account does not belong to this workspace.")
    elif account.entity_id != payment.entity_id:
        errors.append("Source account does not belong to the selected entity.")
    elif account.currency != payment.currency:
        errors.append("Payment currency must match the source account currency.")
    if payment.currency not in allowed_currencies:
        errors.append("Payment currency is not allowed by the selected profile.")
    if payment.amount > profile.maximum_amount:
        errors.append(
            f"Payment exceeds the profile limit of {_money(profile.maximum_amount)}."
        )
    if payment.requested_execution_date < today:
        errors.append("Requested execution date cannot be in the past.")
    if not re.fullmatch(r"[A-Z0-9]{5,34}", account_identifier):
        errors.append("Beneficiary account must contain 5 to 34 letters or digits.")
    if not re.fullmatch(r"[A-Z]{2}", payment.beneficiary_country_code):
        errors.append("Beneficiary country must be a two-letter country code.")
    return errors


def _serialize_payment(session: Session, payment: Payment) -> PaymentResponse:
    entity = session.get(Entity, payment.entity_id)
    account = session.get(BankAccount, payment.source_account_id)
    profile = session.get(PaymentProfile, payment.payment_profile_id)
    creator = session.get(User, payment.created_by_user_id)
    return PaymentResponse(
        id=payment.id,
        entity_id=payment.entity_id,
        entity_name=entity.name if entity else "Unknown entity",
        source_account_id=payment.source_account_id,
        source_account_name=account.account_name if account else "Unknown account",
        payment_profile_id=payment.payment_profile_id,
        payment_profile_name=profile.name if profile else "Unknown profile",
        profile_version=payment.profile_version,
        beneficiary_name=payment.beneficiary_name,
        beneficiary_account=payment.beneficiary_account,
        beneficiary_country_code=payment.beneficiary_country_code,
        amount=_money(payment.amount),
        currency=payment.currency,
        requested_execution_date=payment.requested_execution_date,
        reference=payment.reference,
        status=payment.status,
        validation_status=payment.validation_status,
        validation_errors=json.loads(payment.validation_detail),
        created_by_user_id=payment.created_by_user_id,
        created_by_name=creator.display_name if creator else "Unknown user",
        submitted_by_user_id=payment.submitted_by_user_id,
        decided_by_user_id=payment.decided_by_user_id,
        created_at=payment.created_at.isoformat(),
        submitted_at=payment.submitted_at.isoformat() if payment.submitted_at else None,
        decided_at=payment.decided_at.isoformat() if payment.decided_at else None,
        can_export=payment.status == "approved",
    )


def list_payment_profiles(
    session: Session, *, workspace_id: str, actor_user_id: str
) -> list[PaymentProfileResponse]:
    require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        allowed_roles=PAYMENT_ROLES,
    )
    profiles = session.scalars(
        select(PaymentProfile)
        .where(PaymentProfile.workspace_id == workspace_id)
        .order_by(PaymentProfile.name, PaymentProfile.version)
    ).all()
    return [
        PaymentProfileResponse(
            id=profile.id,
            name=profile.name,
            version=profile.version,
            message_type=profile.message_type,
            allowed_currencies=profile.allowed_currencies.split(","),
            maximum_amount=_money(profile.maximum_amount),
        )
        for profile in profiles
    ]


def list_payments(
    session: Session, *, workspace_id: str, actor_user_id: str
) -> list[PaymentResponse]:
    require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        allowed_roles=PAYMENT_ROLES,
    )
    payments = session.scalars(
        select(Payment)
        .where(Payment.workspace_id == workspace_id)
        .order_by(Payment.created_at.desc())
    ).all()
    return [_serialize_payment(session, payment) for payment in payments]


def create_payment(
    session: Session,
    *,
    workspace_id: str,
    actor_user_id: str,
    request: PaymentCreate,
) -> PaymentResponse:
    require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        allowed_roles=PREPARATION_ROLES,
    )
    profile = _get_profile(
        session, workspace_id=workspace_id, profile_id=request.payment_profile_id
    )
    now = datetime.now(UTC)
    payment = Payment(
        id=str(uuid4()),
        workspace_id=workspace_id,
        entity_id=request.entity_id,
        source_account_id=request.source_account_id,
        payment_profile_id=profile.id,
        profile_version=profile.version,
        beneficiary_name=request.beneficiary_name.strip(),
        beneficiary_account=re.sub(r"\s+", "", request.beneficiary_account).upper(),
        beneficiary_country_code=request.beneficiary_country_code.upper(),
        amount=request.amount,
        currency=request.currency.upper(),
        requested_execution_date=request.requested_execution_date,
        reference=request.reference.strip(),
        status="draft",
        validation_status="pending",
        validation_detail="[]",
        created_by_user_id=actor_user_id,
        submitted_by_user_id=None,
        decided_by_user_id=None,
        created_at=now,
        submitted_at=None,
        decided_at=None,
    )
    errors = _validation_errors(
        payment,
        profile=profile,
        account=session.get(BankAccount, payment.source_account_id),
        entity=session.get(Entity, payment.entity_id),
        today=now.date(),
    )
    payment.validation_status = "failed" if errors else "passed"
    payment.validation_detail = json.dumps(errors)
    session.add(payment)
    _audit(
        session,
        payment=payment,
        actor_user_id=actor_user_id,
        action="payment.created",
        detail={
            "status": payment.status,
            "validation_status": payment.validation_status,
            "profile_version": payment.profile_version,
        },
        now=now,
    )
    session.commit()
    return _serialize_payment(session, payment)


def submit_payment(
    session: Session, *, workspace_id: str, payment_id: str, actor_user_id: str
) -> PaymentResponse:
    require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        allowed_roles=PREPARATION_ROLES,
    )
    payment = _get_payment(session, workspace_id=workspace_id, payment_id=payment_id)
    if payment.status not in {"draft", "rejected"}:
        raise PaymentStateError("Only draft or rejected payments can be submitted.")
    if payment.created_by_user_id != actor_user_id:
        raise PaymentStateError("Only the payment maker can submit this payment.")

    profile = _get_profile(
        session, workspace_id=workspace_id, profile_id=payment.payment_profile_id
    )
    now = datetime.now(UTC)
    errors = _validation_errors(
        payment,
        profile=profile,
        account=session.get(BankAccount, payment.source_account_id),
        entity=session.get(Entity, payment.entity_id),
        today=now.date(),
    )
    payment.validation_status = "failed" if errors else "passed"
    payment.validation_detail = json.dumps(errors)
    if errors:
        session.commit()
        raise PaymentValidationError("Payment validation failed: " + " ".join(errors))

    payment.status = "pending_approval"
    payment.submitted_by_user_id = actor_user_id
    payment.submitted_at = now
    payment.decided_by_user_id = None
    payment.decided_at = None
    _audit(
        session,
        payment=payment,
        actor_user_id=actor_user_id,
        action="payment.submitted",
        detail={"status": payment.status},
        now=now,
    )
    session.commit()
    return _serialize_payment(session, payment)


def decide_payment(
    session: Session,
    *,
    workspace_id: str,
    payment_id: str,
    actor_user_id: str,
    decision: str,
    comment: str,
) -> PaymentResponse:
    require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        allowed_roles=APPROVAL_ROLES,
    )
    payment = _get_payment(session, workspace_id=workspace_id, payment_id=payment_id)
    if payment.status != "pending_approval":
        raise PaymentStateError("Only payments pending approval can be decided.")
    if actor_user_id in {payment.created_by_user_id, payment.submitted_by_user_id}:
        raise PaymentStateError("Maker/checker requires a different approver.")
    if decision not in {"approved", "rejected"}:
        raise PaymentStateError("Decision must be approved or rejected.")

    now = datetime.now(UTC)
    payment.status = decision
    payment.decided_by_user_id = actor_user_id
    payment.decided_at = now
    session.add(
        PaymentDecision(
            id=str(uuid4()),
            payment_id=payment.id,
            actor_user_id=actor_user_id,
            decision=decision,
            comment=comment.strip(),
            created_at=now,
        )
    )
    _audit(
        session,
        payment=payment,
        actor_user_id=actor_user_id,
        action=f"payment.{decision}",
        detail={"status": decision, "comment": comment.strip()},
        now=now,
    )
    session.commit()
    return _serialize_payment(session, payment)


def list_payment_audit_events(
    session: Session,
    *,
    workspace_id: str,
    payment_id: str,
    actor_user_id: str,
) -> list[PaymentAuditEventResponse]:
    require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        allowed_roles=PAYMENT_ROLES,
    )
    _get_payment(session, workspace_id=workspace_id, payment_id=payment_id)
    events = session.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.workspace_id == workspace_id,
            AuditEvent.target_type == "payment",
            AuditEvent.target_id == payment_id,
        )
        .order_by(AuditEvent.created_at, AuditEvent.id)
    ).all()
    responses: list[PaymentAuditEventResponse] = []
    for event in events:
        actor = session.get(User, event.actor_user_id) if event.actor_user_id else None
        responses.append(
            PaymentAuditEventResponse(
                id=event.id,
                action=event.action,
                actor_user_id=event.actor_user_id,
                actor_name=actor.display_name if actor else "System",
                detail=json.loads(event.detail),
                created_at=event.created_at.isoformat(),
            )
        )
    return responses


def _build_iso20022(
    payment: Payment, *, entity: Entity, account: BankAccount
) -> str:
    namespace = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"
    ET.register_namespace("", namespace)

    def element(parent: ET.Element, name: str, text: str | None = None) -> ET.Element:
        child = ET.SubElement(parent, f"{{{namespace}}}{name}")
        if text is not None:
            child.text = text
        return child

    document = ET.Element(f"{{{namespace}}}Document")
    initiation = element(document, "CstmrCdtTrfInitn")
    group = element(initiation, "GrpHdr")
    element(group, "MsgId", f"TREASURFY-{payment.id}")
    timestamp = payment.decided_at or payment.created_at
    element(group, "CreDtTm", timestamp.isoformat())
    element(group, "NbOfTxs", "1")
    element(group, "CtrlSum", _money(payment.amount))
    initiator = element(group, "InitgPty")
    element(initiator, "Nm", entity.name)

    info = element(initiation, "PmtInf")
    element(info, "PmtInfId", f"PMT-{payment.id}")
    element(info, "PmtMtd", "TRF")
    element(info, "NbOfTxs", "1")
    element(info, "CtrlSum", _money(payment.amount))
    element(info, "ReqdExctnDt", payment.requested_execution_date.isoformat())
    debtor = element(info, "Dbtr")
    element(debtor, "Nm", entity.name)
    debtor_account = element(info, "DbtrAcct")
    debtor_id = element(debtor_account, "Id")
    other = element(debtor_id, "Othr")
    element(other, "Id", account.id)

    transaction = element(info, "CdtTrfTxInf")
    payment_id = element(transaction, "PmtId")
    element(payment_id, "EndToEndId", payment.reference)
    amount = element(transaction, "Amt")
    instructed = element(amount, "InstdAmt", _money(payment.amount))
    instructed.set("Ccy", payment.currency)
    creditor = element(transaction, "Cdtr")
    element(creditor, "Nm", payment.beneficiary_name)
    address = element(creditor, "PstlAdr")
    element(address, "Ctry", payment.beneficiary_country_code)
    creditor_account = element(transaction, "CdtrAcct")
    creditor_id = element(creditor_account, "Id")
    if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{13,32}", payment.beneficiary_account):
        element(creditor_id, "IBAN", payment.beneficiary_account)
    else:
        other_creditor = element(creditor_id, "Othr")
        element(other_creditor, "Id", payment.beneficiary_account)
    remittance = element(transaction, "RmtInf")
    element(remittance, "Ustrd", payment.reference)

    output = BytesIO()
    ET.ElementTree(document).write(
        output, encoding="utf-8", xml_declaration=True, short_empty_elements=True
    )
    return output.getvalue().decode("utf-8")


def export_iso20022(
    session: Session,
    *,
    workspace_id: str,
    payment_id: str,
    actor_user_id: str,
) -> tuple[str, str]:
    require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        allowed_roles={
            MembershipRole.ADMIN,
            MembershipRole.PREPARER,
            MembershipRole.APPROVER,
        },
    )
    payment = _get_payment(session, workspace_id=workspace_id, payment_id=payment_id)
    if payment.status != "approved":
        raise PaymentStateError("Only approved payments can be exported.")

    existing = session.scalar(
        select(PaymentExport)
        .where(PaymentExport.payment_id == payment.id)
        .order_by(PaymentExport.created_at)
    )
    if existing:
        return existing.content, existing.content_sha256

    entity = session.get(Entity, payment.entity_id)
    account = session.get(BankAccount, payment.source_account_id)
    if entity is None or account is None:
        raise PaymentValidationError("Payment source data is no longer available.")
    content = _build_iso20022(payment, entity=entity, account=account)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    now = datetime.now(UTC)
    session.add(
        PaymentExport(
            id=str(uuid4()),
            payment_id=payment.id,
            actor_user_id=actor_user_id,
            format="pain.001.001.03-demo",
            content_sha256=digest,
            content=content,
            created_at=now,
        )
    )
    _audit(
        session,
        payment=payment,
        actor_user_id=actor_user_id,
        action="payment.exported",
        detail={"format": "pain.001.001.03-demo", "sha256": digest},
        now=now,
    )
    session.commit()
    return content, digest
