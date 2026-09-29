"""
Zero-Trust Framework
=====================
"Never trust, always verify." Every user and every command is
re-authenticated and re-authorized on every request, regardless of
whether they are already "inside" the station network.

Contains:
    - MultiFactorAuth      : password + TOTP (time-based one-time code)
    - RBACManager           : role -> permission mapping + @require_permission
    - CommandUplink         : HMAC-signed, timestamped, replay-proof commands
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable

import pyotp


# ---------------------------------------------------------------------------
# 1. Multi-Factor Authentication
# ---------------------------------------------------------------------------

@dataclass
class UserAccount:
    username: str
    password_hash: str
    totp_secret: str
    role: str


class MultiFactorAuth:
    """
    Handles password verification + TOTP (RFC 6238) second factor.

    Example
    -------
    >>> mfa = MultiFactorAuth()
    >>> secret = mfa.enroll_user("dr_sharma", "S3curePass!", role="scientist")
    >>> otp = pyotp.TOTP(secret).now()          # normally generated on the user's phone app
    >>> mfa.authenticate("dr_sharma", "S3curePass!", otp)
    True
    """

    def __init__(self) -> None:
        self._users: dict[str, UserAccount] = {}

    @staticmethod
    def _hash_password(password: str, salt: str = "antarctic-station") -> str:
        # PBKDF2-HMAC-SHA256: slow, salted hashing -> resists brute force / rainbow tables
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100_000
        ).hex()

    def enroll_user(self, username: str, password: str, role: str) -> str:
        """Registers a new user and returns their TOTP secret (shown once, e.g. as a QR code)."""
        totp_secret = pyotp.random_base32()
        self._users[username] = UserAccount(
            username=username,
            password_hash=self._hash_password(password),
            totp_secret=totp_secret,
            role=role,
        )
        return totp_secret

    def get_provisioning_uri(self, username: str, issuer: str = "AntarcticaStationGateway") -> str:
        """URI that can be rendered as a QR code for an authenticator app (Google Authenticator etc.)."""
        user = self._users[username]
        return pyotp.TOTP(user.totp_secret).provisioning_uri(name=username, issuer_name=issuer)

    def authenticate(self, username: str, password: str, otp_code: str) -> bool:
        """Returns True only if BOTH the password and the current TOTP code are correct."""
        user = self._users.get(username)
        if user is None:
            return False
        password_ok = hmac.compare_digest(user.password_hash, self._hash_password(password))
        otp_ok = pyotp.TOTP(user.totp_secret).verify(otp_code, valid_window=1)
        return password_ok and otp_ok

    def role_of(self, username: str) -> str | None:
        user = self._users.get(username)
        return user.role if user else None


# ---------------------------------------------------------------------------
# 2. Role-Based Access Control
# ---------------------------------------------------------------------------

# Example role -> permission map for a research station.
DEFAULT_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "scientist": {"view_sensor_data", "view_dashboard", "send_science_message"},
    "station_operator": {
        "view_sensor_data", "view_dashboard", "send_science_message",
        "control_non_critical_systems", "acknowledge_alerts",
    },
    "admin": {
        "view_sensor_data", "view_dashboard", "send_science_message",
        "control_non_critical_systems", "acknowledge_alerts",
        "control_critical_systems", "manage_users", "issue_evacuation",
    },
}


class RBACManager:
    """
    Example
    -------
    >>> rbac = RBACManager()
    >>> rbac.has_permission("scientist", "control_critical_systems")
    False
    >>> rbac.has_permission("admin", "control_critical_systems")
    True
    """

    def __init__(self, role_permissions: dict[str, set[str]] | None = None) -> None:
        self.role_permissions = role_permissions or DEFAULT_ROLE_PERMISSIONS

    def has_permission(self, role: str, permission: str) -> bool:
        return permission in self.role_permissions.get(role, set())

    def require_permission(self, permission: str) -> Callable:
        """
        Decorator for view functions. Expects the wrapped function to be
        called with a `role` keyword argument (the caller's already-verified role).
        Raises PermissionError if the role lacks the permission.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, role: str, **kwargs):
                if not self.has_permission(role, permission):
                    raise PermissionError(
                        f"Role '{role}' lacks permission '{permission}' (zero-trust denial)."
                    )
                return func(*args, role=role, **kwargs)
            return wrapper
        return decorator


# ---------------------------------------------------------------------------
# 3. Secure Command Uplinks
# ---------------------------------------------------------------------------

@dataclass
class SignedCommand:
    command: str
    issuer: str
    timestamp: float
    nonce: str
    signature: str


class CommandUplink:
    """
    Signs and verifies commands sent UP to the station (e.g. from Delhi/Goa
    control room to the Antarctic station), preventing:
      - Forgery      (signature won't validate without the shared key)
      - Replay       (nonce cache + timestamp expiry)
      - Tampering    (any change to the command invalidates the signature)

    Example
    -------
    >>> uplink = CommandUplink(shared_key=b"super-secret-preshared-key")
    >>> signed = uplink.sign_command("SHUTDOWN_GENERATOR_2", issuer="admin")
    >>> uplink.verify_command(signed)
    True
    >>> uplink.verify_command(signed)   # replay attempt
    False
    """

    def __init__(self, shared_key: bytes, max_age_seconds: int = 30) -> None:
        self._key = shared_key
        self._max_age = max_age_seconds
        self._seen_nonces: set[str] = set()

    def _signature(self, command: str, issuer: str, timestamp: float, nonce: str) -> str:
        payload = f"{command}|{issuer}|{timestamp}|{nonce}".encode()
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    def sign_command(self, command: str, issuer: str) -> SignedCommand:
        timestamp = time.time()
        nonce = secrets.token_hex(8)
        sig = self._signature(command, issuer, timestamp, nonce)
        return SignedCommand(command, issuer, timestamp, nonce, sig)

    def verify_command(self, signed: SignedCommand) -> bool:
        # 1. Freshness check -> mitigates replay of old captured commands
        if time.time() - signed.timestamp > self._max_age:
            return False
        # 2. Nonce reuse check -> mitigates exact replay within the freshness window
        if signed.nonce in self._seen_nonces:
            return False
        # 3. Signature check -> mitigates forgery/tampering
        expected = self._signature(signed.command, signed.issuer, signed.timestamp, signed.nonce)
        if not hmac.compare_digest(expected, signed.signature):
            return False
        self._seen_nonces.add(signed.nonce)
        return True
