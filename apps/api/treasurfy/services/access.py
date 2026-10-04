from __future__ import annotations

from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.orm import Session

from treasurfy.models import Membership, MembershipRole, Workspace


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceAccessDeniedError(Exception):
    pass


def require_workspace_access(
    session: Session,
    *,
    workspace_id: str,
    actor_user_id: str,
    allowed_roles: Collection[MembershipRole] | None = None,
) -> tuple[Workspace, Membership]:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError

    membership = session.scalar(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == actor_user_id,
        )
    )
    if membership is None:
        raise WorkspaceAccessDeniedError
    if allowed_roles is not None and membership.role not in allowed_roles:
        raise WorkspaceAccessDeniedError

    return workspace, membership
