"""Organisation Portal guards (docs/ORGANISATION_PORTAL.md).

The organisation is always the authenticated user's own organisation; no endpoint accepts an
organisation ID from the request. get_current_user has already rejected inactive accounts, accounts of
organisations that are not active and accounts with a pending password change.
"""

from fastapi import Depends, HTTPException, status

from backend.app.models.organization import ACCOUNT_ORGANISATION, ORG_MANAGER_ROLES, ORG_ROLE_OWNER
from backend.app.models.user import User
from backend.app.security.auth import get_current_user

ORGANISATION_ACCOUNT_REQUIRED = "This page is only available to organisation accounts."
ORGANISATION_ADMIN_REQUIRED = "Organisation administrator access required."


def is_org_manager(user: User) -> bool:
    return user.org_role in ORG_MANAGER_ROLES


def is_org_owner(user: User) -> bool:
    return user.org_role == ORG_ROLE_OWNER


def get_current_org_member(current_user: User = Depends(get_current_user)) -> User:
    if (getattr(current_user, "account_type", None) != ACCOUNT_ORGANISATION
            or not getattr(current_user, "organization_id", None)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ORGANISATION_ACCOUNT_REQUIRED)
    return current_user


def get_current_org_admin(member: User = Depends(get_current_org_member)) -> User:
    if not is_org_manager(member):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ORGANISATION_ADMIN_REQUIRED)
    return member
