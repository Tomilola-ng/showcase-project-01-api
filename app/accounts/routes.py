"""Accounts Routes"""

from datetime import datetime, timezone

from typing import Optional
from fastapi import (APIRouter, BackgroundTasks, File,
                     UploadFile, status, HTTPException, Depends, Response, Query)
from fastapi.security import HTTPBearer
from tortoise.expressions import Q

from app.accounts.enums import UserStatus, UserRole
from app.accounts.models import Account
from app.accounts.schemas import (
    AccountFullPydantic,
    AccountCreatePydantic,
    AccountRead,
    LoginUserSchema,
    ChangePasswordSchema,
    AccountUpdate,
    AccountListResponse,
)
from app.config.pagination import (
    PaginationParams,
    PaginationHelper,
    get_pagination_params,
)
from app.accounts.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user
)

from app.base.models import FileAsset
from app.config.settings import settings
from app.config.storage import r2_storage


router = APIRouter(prefix="/auth", tags=["Accounts"])
security = HTTPBearer()


async def get_user_or_404_by_email(email: str) -> Account:
    """Fetch Account by email field or 404."""
    user = await Account.filter(email=email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(response: Response, data: LoginUserSchema):
    """Login user; return tokens and profile."""
    user = await get_user_or_404_by_email(data.email)
    if user.status != UserStatus.ACTIVE:
        if user.status == UserStatus.SUSPENDED:
            raise HTTPException(status_code=403, detail="User is suspended.")
        if user.status == UserStatus.DEACTIVATED:
            raise HTTPException(status_code=403, detail="User is deactivated.")
        raise HTTPException(status_code=400, detail="User is not active.")
    if not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=400, detail="Incorrect email or password.")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    user.last_login_at = datetime.now(timezone.utc)
    await user.save()

    return {
        "message": "Login Successful",
        "data": {
            "access": access_token,
            "refresh": refresh_token,
            "user": await AccountFullPydantic.from_tortoise_orm(user),
        },
    }


@router.post("/logout", status_code=status.HTTP_200_OK, dependencies=[Depends(security)])
async def logout_user(response: Response, current_user: Account = Depends(get_current_user)):
    """Logout user; clear tokens."""
    response.delete_cookie(key="access", path=settings.AUTH_COOKIE_PATH)
    response.delete_cookie(key="refresh", path=settings.AUTH_COOKIE_PATH)
    return {"message": "Logout successful"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(data: AccountCreatePydantic, background_tasks: BackgroundTasks):
    """Register new user; send activation email if email provided."""
    if data.email:
        if await Account.filter(email=data.email).exists():
            raise HTTPException(
                status_code=400, detail="Email already registered.")

    user_data = data.model_dump(exclude_unset=True)
    user_data["password"] = hash_password(user_data["password"])
    user = await Account.create(**user_data)

    return {
        "message": "User Created",
        "data": await AccountFullPydantic.from_tortoise_orm(user),
    }


@router.get("/current-user", status_code=status.HTTP_200_OK, dependencies=[Depends(security)])
async def get_current_user_data(current_user: Account = Depends(get_current_user)):
    """Get authenticated user's profile."""
    await current_user.fetch_related("image")
    user_out = AccountRead.model_validate(current_user)
    return {
        "message": "User Retrieved",
        "data": user_out,
    }


@router.get(
    "/users",
    response_model=AccountListResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(security)]
)
async def list_users(
    pagination_params: PaginationParams = Depends(get_pagination_params),
    search: Optional[str] = Query(
        None, description="Search users by first name or last name"),
    exclude_current: bool = Query(
        True, description="Exclude current user from results"),
    current_user: Account = Depends(get_current_user)
):
    """
    List all users with pagination.

    - Returns paginated list of users
    - Can search by first name or last name
    - Optionally excludes current user from results
    - Useful for finding users to start a chat with
    """
    # Build queryset
    queryset = Account.filter(
        status=UserStatus.ACTIVE).prefetch_related("image")

    # Exclude current user if requested
    if exclude_current:
        queryset = queryset.exclude(id=current_user.id)

    # Apply search filter if provided
    if search:
        search_term = search.strip()
        queryset = queryset.filter(
            Q(first_name__icontains=search_term) | Q(
                last_name__icontains=search_term)
        )

    # Order by name
    queryset = queryset.order_by("first_name", "last_name")

    # Paginate
    items, meta = await PaginationHelper.paginate_queryset(queryset, pagination_params)

    # Convert to AccountRead schema
    account_reads = [
        AccountRead.model_validate(account) for account in items
    ]

    return PaginationHelper.create_paginated_response(account_reads, meta)


@router.patch("/update-user-image", status_code=status.HTTP_200_OK, dependencies=[Depends(security)])
async def update_user_image(file: UploadFile = File(...), current_user: Account = Depends(get_current_user)):
    """Partially update authenticated user image."""
    key = await r2_storage.upload_file(file=file, folder="user_images")

    try:
        content = await file.read()
        file_size = len(content) if content is not None else None
    finally:
        await file.seek(0)

    file = await FileAsset.create(
        key=key,
        alt_text=f"{current_user.first_name} Image",
        content_type=file.content_type,
        file_size=file_size,
    )
    current_user.image = file
    await current_user.save()
    return {
        "message": "User Updated Successfully",
        "data": await AccountFullPydantic.from_tortoise_orm(current_user),
    }


@router.patch("/update-profile", status_code=status.HTTP_200_OK, dependencies=[Depends(security)])
async def update_user_profile(
    data: AccountUpdate,
    current_user: Account = Depends(get_current_user)
):
    """Update authenticated user's profile."""
    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(current_user, key, value)

    await current_user.save()
    await current_user.fetch_related("image")

    return {
        "message": "Profile updated successfully",
        "data": AccountRead.model_validate(current_user),
    }


@router.post("/change-password", status_code=status.HTTP_200_OK, dependencies=[Depends(security)])
async def change_password(data: ChangePasswordSchema, current_user: Account = Depends(get_current_user)):
    """Change password for authenticated user."""
    if not verify_password(data.old_password, current_user.password):
        raise HTTPException(
            status_code=400, detail="Old password is incorrect.")
    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=400, detail="New passwords do not match.")
    current_user.password = hash_password(data.new_password)
    await current_user.save()
    return {"message": "Password changed successfully."}


if settings.ENVIRONMENT == "local":
    @router.post("/make-admin", status_code=status.HTTP_200_OK)
    async def make_user_admin(email: str):
        """
            Make a user an admin.
            Only available in local environment.
        """
        user = await Account.get_or_none(email=email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        user.role = UserRole.ADMIN
        await user.save()

        return {"message": f"User {email} is now an admin."}
