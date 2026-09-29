"""
REST API for the Secure Cybersecurity Gateway.

Exposes each sub-component as a JSON endpoint under /api/gateway/*.
Any teammate's frontend (the combined website) can call these directly.

NOTE ON DEMO STATE: for hackathon-demo simplicity, secrets/users/monitors
live in memory (module-level singletons) rather than a database. Swap
`_mfa`, `_uplink`, etc. for real persistent stores when integrating with
the team's actual backend/database.
"""

from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

from .advanced_cryptography import (
    EndToEndEncryption,
    LightweightCipher,
    PostQuantumKeyExchange,
)
from .link_integrity import (
    AntiSpoofingVerifier,
    RFLinkReliability,
    VSATMonitor,
    read_live_sample,
)
from .zero_trust import CommandUplink, MultiFactorAuth, RBACManager

gateway_bp = Blueprint("cybersecurity_gateway", __name__, url_prefix="/api/gateway")

# --- module-level singletons (demo-scope state; swap for real DB in production) ---
_mfa = MultiFactorAuth()
_rbac = RBACManager()
_uplink = CommandUplink(shared_key=os.environ.get("GATEWAY_UPLINK_KEY", "demo-uplink-key").encode())
_pqc = PostQuantumKeyExchange()
_beacon_verifier = AntiSpoofingVerifier(shared_key=os.environ.get("GATEWAY_BEACON_KEY", "demo-beacon-key").encode())
_vsat_monitor = VSATMonitor()
_reliability = RFLinkReliability()

# Seed one demo user so the endpoints are testable out of the box.
_DEMO_TOTP_SECRET = _mfa.enroll_user("demo_admin", "ChangeMe!123", role="admin")


# ---------------------------------------------------------------------------
# Zero-Trust Framework endpoints
# ---------------------------------------------------------------------------

@gateway_bp.route("/zero-trust/login", methods=["POST"])
def login():
    """Body: {"username": "...", "password": "...", "otp": "..."}"""
    data = request.get_json(force=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    otp = data.get("otp", "")

    if _mfa.authenticate(username, password, otp):
        role = _mfa.role_of(username)
        return jsonify({"authenticated": True, "username": username, "role": role})
    return jsonify({"authenticated": False, "error": "Invalid credentials or OTP"}), 401


@gateway_bp.route("/zero-trust/check-permission", methods=["POST"])
def check_permission():
    """Body: {"role": "...", "permission": "..."}"""
    data = request.get_json(force=True) or {}
    role = data.get("role", "")
    permission = data.get("permission", "")
    return jsonify({"role": role, "permission": permission, "allowed": _rbac.has_permission(role, permission)})


@gateway_bp.route("/zero-trust/sign-command", methods=["POST"])
def sign_command():
    """Body: {"command": "...", "issuer": "..."}"""
    data = request.get_json(force=True) or {}
    signed = _uplink.sign_command(data.get("command", ""), data.get("issuer", "unknown"))
    return jsonify(signed.__dict__)


@gateway_bp.route("/zero-trust/verify-command", methods=["POST"])
def verify_command():
    """Body: full signed-command dict as returned by /sign-command."""
    from .zero_trust import SignedCommand
    data = request.get_json(force=True) or {}
    try:
        signed = SignedCommand(**data)
    except TypeError:
        return jsonify({"error": "Malformed signed command"}), 400
    return jsonify({"valid": _uplink.verify_command(signed)})


# ---------------------------------------------------------------------------
# Advanced Cryptography endpoints
# ---------------------------------------------------------------------------

@gateway_bp.route("/crypto/pqc/generate-keypair", methods=["GET"])
def pqc_generate_keypair():
    public_key, private_key = _pqc.generate_keypair()
    # NOTE: in a real deployment the private key never leaves the station's
    # secure enclave. It's returned here only for hackathon-demo purposes.
    return jsonify({
        "public_key_hex": public_key.hex(),
        "private_key_hex": private_key.hex(),
        "algorithm": "ML-KEM-768 (NIST FIPS 203 / CRYSTALS-Kyber)",
    })


@gateway_bp.route("/crypto/pqc/encapsulate", methods=["POST"])
def pqc_encapsulate():
    """Body: {"public_key_hex": "..."}"""
    data = request.get_json(force=True) or {}
    public_key = bytes.fromhex(data["public_key_hex"])
    shared_secret, ciphertext = _pqc.encapsulate(public_key)
    return jsonify({"shared_secret_hex": shared_secret.hex(), "ciphertext_hex": ciphertext.hex()})


@gateway_bp.route("/crypto/lightweight/encrypt", methods=["POST"])
def lightweight_encrypt():
    """Body: {"plaintext": "...", "key_hex": "..." (optional)}"""
    data = request.get_json(force=True) or {}
    key = bytes.fromhex(data["key_hex"]) if data.get("key_hex") else None
    cipher = LightweightCipher(key=key)
    packet = cipher.encrypt(data.get("plaintext", "").encode())
    return jsonify({
        "key_hex": cipher.key.hex(),
        "nonce_hex": packet["nonce"].hex(),
        "ciphertext_hex": packet["ciphertext"].hex(),
        "algorithm": "ASCON-128 (NIST Lightweight Cryptography standard)",
    })


@gateway_bp.route("/crypto/e2e/encrypt", methods=["POST"])
def e2e_encrypt():
    """Body: {"plaintext": "...", "key_hex": "..."} (key_hex normally = PQC shared secret)"""
    data = request.get_json(force=True) or {}
    key = bytes.fromhex(data["key_hex"]) if data.get("key_hex") else os.urandom(32)
    e2e = EndToEndEncryption(key)
    msg = e2e.encrypt(data.get("plaintext", "").encode())
    return jsonify({
        "key_hex": key.hex(),
        "nonce_hex": msg.nonce.hex(),
        "ciphertext_hex": msg.ciphertext.hex(),
        "algorithm": "AES-256-GCM",
    })


# ---------------------------------------------------------------------------
# Link Integrity endpoints
# ---------------------------------------------------------------------------

@gateway_bp.route("/link/vsat-status", methods=["GET"])
def vsat_status():
    status = _vsat_monitor.poll()
    _reliability.record(read_live_sample())  # feed the same tick into reliability tracking
    return jsonify(status)


@gateway_bp.route("/link/reliability-report", methods=["GET"])
def reliability_report():
    return jsonify(_reliability.report())


@gateway_bp.route("/link/beacon/sign", methods=["POST"])
def sign_beacon():
    """Body: {"payload": "STATION_MAITRI_OK"}"""
    data = request.get_json(force=True) or {}
    return jsonify(_beacon_verifier.sign_beacon(data.get("payload", "")))


@gateway_bp.route("/link/beacon/verify", methods=["POST"])
def verify_beacon():
    """Body: {"payload": "...", "signature": "..."}"""
    data = request.get_json(force=True) or {}
    return jsonify({"valid": _beacon_verifier.verify_beacon(data)})


# ---------------------------------------------------------------------------
# Health check -- useful for the team's main app to confirm this module is wired in
# ---------------------------------------------------------------------------

@gateway_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "module": "Secure Cybersecurity Gateway",
        "status": "online",
        "components": ["zero_trust", "advanced_cryptography", "link_integrity"],
    })
