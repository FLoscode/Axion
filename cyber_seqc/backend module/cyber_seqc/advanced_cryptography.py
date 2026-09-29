"""
Advanced Cryptography
=======================
Protects data confidentiality/integrity in storage and over the
satellite link, and hedges against future quantum-computing attacks.

Contains:
    - PostQuantumKeyExchange : ML-KEM-768 (Kyber) key encapsulation -- NIST FIPS 203 standard
    - LightweightCipher      : ASCON-128 authenticated encryption -- NIST Lightweight Crypto winner
    - EndToEndEncryption     : AES-256-GCM for bulk data, keyed from the PQC-derived secret
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import ascon
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from kyber_py.ml_kem import ML_KEM_768


# ---------------------------------------------------------------------------
# 1. Post-Quantum Cryptography (PQC) -- key exchange
# ---------------------------------------------------------------------------

class PostQuantumKeyExchange:
    """
    ML-KEM-768 (the FIPS-203-standardized version of CRYSTALS-Kyber) key
    encapsulation. Classical algorithms like RSA/ECDH are breakable by a
    sufficiently large quantum computer (Shor's algorithm); ML-KEM is
    designed to resist that. Used to agree a shared secret between the
    station and mission control, which then seeds the E2E symmetric cipher.

    Example
    -------
    >>> pqc = PostQuantumKeyExchange()
    >>> station_public_key, station_private_key = pqc.generate_keypair()
    >>> shared_secret_sender, ciphertext = pqc.encapsulate(station_public_key)
    >>> shared_secret_receiver = pqc.decapsulate(station_private_key, ciphertext)
    >>> shared_secret_sender == shared_secret_receiver
    True
    """

    def __init__(self) -> None:
        self._scheme = ML_KEM_768

    def generate_keypair(self) -> tuple[bytes, bytes]:
        """Returns (public_key, private_key). Public key is safely shareable over the link."""
        encapsulation_key, decapsulation_key = self._scheme.keygen()
        return encapsulation_key, decapsulation_key

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        """Sender side: derives a shared secret and a ciphertext to send to the key owner."""
        shared_secret, ciphertext = self._scheme.encaps(public_key)
        return shared_secret, ciphertext

    def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """Receiver side: recovers the same shared secret from the ciphertext."""
        return self._scheme.decaps(private_key, ciphertext)


# ---------------------------------------------------------------------------
# 2. NIST Lightweight Cryptography -- for constrained sensor/IoT nodes
# ---------------------------------------------------------------------------

class LightweightCipher:
    """
    ASCON-128 authenticated encryption -- selected by NIST in Feb 2023 as
    the standard for lightweight cryptography, purpose-built for
    low-power/low-memory devices (weather sensors, seismographs, IoT
    nodes around the station) where full AES/RSA is too heavy.

    Example
    -------
    >>> cipher = LightweightCipher(key=os.urandom(16))
    >>> packet = cipher.encrypt(b"temp=-42.3C wind=18kt")
    >>> cipher.decrypt(packet)
    b'temp=-42.3C wind=18kt'
    """

    def __init__(self, key: bytes | None = None) -> None:
        self.key = key or os.urandom(16)  # 128-bit key

    def encrypt(self, plaintext: bytes, associated_data: bytes = b"") -> dict:
        nonce = os.urandom(16)
        ciphertext = ascon.encrypt(
            self.key, nonce, associated_data, plaintext, variant="Ascon-128"
        )
        return {"nonce": nonce, "ciphertext": ciphertext, "aad": associated_data}

    def decrypt(self, packet: dict) -> bytes:
        return ascon.decrypt(
            self.key, packet["nonce"], packet["aad"], packet["ciphertext"], variant="Ascon-128"
        )


# ---------------------------------------------------------------------------
# 3. End-to-End Encryption -- bulk data (telemetry, files, chat)
# ---------------------------------------------------------------------------

@dataclass
class EncryptedMessage:
    nonce: bytes
    ciphertext: bytes


class EndToEndEncryption:
    """
    AES-256-GCM for the actual payloads (science data, files, operator
    messages), keyed from a 32-byte secret -- normally the shared secret
    produced by PostQuantumKeyExchange, so the symmetric key itself is
    quantum-safe to distribute, while AES-GCM keeps bulk encryption fast.

    Example
    -------
    >>> shared_secret = os.urandom(32)  # in practice: from PostQuantumKeyExchange
    >>> e2e = EndToEndEncryption(shared_secret)
    >>> msg = e2e.encrypt(b"Station Maitri: ice-core sample log attached")
    >>> e2e.decrypt(msg)
    b'Station Maitri: ice-core sample log attached'
    """

    def __init__(self, key: bytes) -> None:
        if len(key) < 32:
            key = key.ljust(32, b"0")  # pad/derive to 256-bit if a shorter key slips through
        self._aesgcm = AESGCM(key[:32])

    def encrypt(self, plaintext: bytes, associated_data: bytes | None = None) -> EncryptedMessage:
        nonce = os.urandom(12)  # 96-bit nonce, standard for GCM
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data)
        return EncryptedMessage(nonce=nonce, ciphertext=ciphertext)

    def decrypt(self, message: EncryptedMessage, associated_data: bytes | None = None) -> bytes:
        return self._aesgcm.decrypt(message.nonce, message.ciphertext, associated_data)
