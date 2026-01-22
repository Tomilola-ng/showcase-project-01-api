"""Accounts models"""

import uuid

from tortoise import fields, models
from app.accounts.enums import UserRole, UserStatus


class Account(models.Model):
    """
    Table: accounts
    """

    id = fields.UUIDField(pk=True, default=uuid.uuid4)

    role = fields.CharEnumField(
        UserRole, max_length=50, default=UserRole.REGULAR)
    first_name = fields.CharField(max_length=255)
    last_name = fields.CharField(max_length=255)
    image = fields.ForeignKeyField(
        "models.FileAsset", related_name="account_images", to_field="id", null=True, on_delete=fields.SET_NULL
    )

    state = fields.CharField(max_length=255, null=True)
    country = fields.CharField(max_length=255, null=True)
    email = fields.CharField(max_length=255, null=True, unique=True)
    phone_number = fields.CharField(max_length=20, null=True)
    password = fields.CharField(max_length=255)

    status = fields.CharEnumField(
        UserStatus, max_length=50, default=UserStatus.ACTIVE)
    last_login_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        """Meta class for Account model"""
        table = "accounts"
        indexes = [
            ("email",),
            ("role",),
            ("status",),
            ("role", "status"),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - ({self.role})"
