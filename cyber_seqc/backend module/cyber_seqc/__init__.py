"""
Secure Cybersecurity Gateway
=============================
Component of the "Digital Platform for Efficient Remote Management of
Indian Antarctic Research Stations" (SIH 2026 - Ministry of Earth Sciences).

This package is self-contained and exposes a Flask Blueprint
`gateway_bp`, so any teammate assembling the final website only needs:

    from cybersecurity_gateway import gateway_bp
    app.register_blueprint(gateway_bp)

Sub-modules:
    zero_trust.py            -> MFA, RBAC, Secure Command Uplinks
    advanced_cryptography.py -> PQC (ML-KEM/Kyber), NIST Lightweight (ASCON), E2E (AES-GCM)
    link_integrity.py        -> Anti-Jamming/Spoofing, VSAT Monitoring, RF Reliability
    routes.py                -> REST API wiring all of the above together
"""

from .routes import gateway_bp

__all__ = ["gateway_bp"]
