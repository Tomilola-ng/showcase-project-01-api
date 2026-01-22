"""
    User Role Enum for Accounts
"""

from enum import Enum


class UserRole(str, Enum):
    """User roles within the platform."""
    REGULAR = "regular"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User account status within the platform."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    DEACTIVATED = "deactivated"

