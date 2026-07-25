from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_superuser, require_permission
from app.core.security import get_password_hash
from app.database import get_db
from app.models import Permission, Role, User
from app.schemas.auth import (
    PermissionCreate,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    UserResponse,
    UserRoleUpdate,
    UserUpdate,
)

router = APIRouter()


@router.get("/roles/", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
):
    return db.query(Role).all()


@router.get("/permissions/", response_model=List[PermissionResponse])
async def list_permissions(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    return db.query(Permission).all()


@router.post("/roles/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    if db.query(Role).filter(Role.name == role_data.name).first():
        raise HTTPException(status_code=400, detail="Role already exists")
    role = Role(name=role_data.name, description=role_data.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.post("/permissions/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission_data: PermissionCreate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    if db.query(Permission).filter(Permission.name == permission_data.name).first():
        raise HTTPException(status_code=400, detail="Permission already exists")
    permission = Permission(name=permission_data.name, description=permission_data.description)
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(role)
    db.commit()
    return {"message": "Role deleted successfully"}


@router.put("/roles/{role_id}/permissions")
async def update_role_permissions(
    role_id: str,
    permission_ids: List[str],
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
    if len(permissions) != len(permission_ids):
        raise HTTPException(status_code=400, detail="One or more permission IDs are invalid")
    role.permissions = permissions
    db.commit()
    return {"message": "Role permissions updated successfully"}


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
):
    return db.query(User).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_permission("users:read")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(require_permission("users:write")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_update.email and user_update.email != user.email:
        if db.query(User).filter(User.email == user_update.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = user_update.email
    if user_update.name is not None:
        user.name = user_update.name
    if user_update.password:
        user.hashed_password = get_password_hash(user_update.password)
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/roles", response_model=UserResponse)
async def update_user_roles(
    user_id: str,
    role_update: UserRoleUpdate,
    current_user: User = Depends(require_permission("users:write")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = db.query(Role).filter(Role.id.in_(role_update.role_ids)).all()
    if len(roles) != len(role_update.role_ids):
        raise HTTPException(status_code=400, detail="One or more role IDs are invalid")
    user.roles = roles
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_permission("users:write")),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
