from __future__ import annotations

import base64
import os
from typing import Protocol

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.shared.settings import (
    CREDENTIAL_MASTER_KEY_ENV as SETTINGS_CREDENTIAL_MASTER_KEY_ENV,
    get_settings,
)
from app.shared.runtime.errors import ConfigurationError

CREDENTIAL_MASTER_KEY_ENV = SETTINGS_CREDENTIAL_MASTER_KEY_ENV
AES_KEY_BYTES = 32
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16
NONCE_BYTES = 12
ENCRYPTION_PAYLOAD_VERSION = "v1"


class CredentialCipher(Protocol):
    def encrypt(self, plaintext: str) -> str: ...

    def decrypt(self, encrypted_payload: str) -> str: ...


class CredentialCrypto:
    def __init__(self, master_key: str | None = None) -> None:
        self._master_key = self._load_master_key(master_key)

    def encrypt(self, plaintext: str) -> str:
        salt = os.urandom(SALT_BYTES)
        nonce = os.urandom(NONCE_BYTES)
        cipher_text = AESGCM(self._derive_key(salt)).encrypt(
            nonce,
            plaintext.encode("utf-8"),
            None,
        )
        return ":".join(
            [
                ENCRYPTION_PAYLOAD_VERSION,
                _urlsafe_b64encode(salt),
                _urlsafe_b64encode(nonce),
                _urlsafe_b64encode(cipher_text),
            ]
        )

    def decrypt(self, encrypted_payload: str) -> str:
        version, salt, nonce, cipher_text = self._parse_payload(encrypted_payload)
        if version != ENCRYPTION_PAYLOAD_VERSION:
            raise ConfigurationError(
                f"Unsupported credential encryption payload version: {version}"
            )
        plaintext = AESGCM(self._derive_key(salt)).decrypt(nonce, cipher_text, None)
        return plaintext.decode("utf-8")

    def _load_master_key(self, master_key: str | None) -> bytes:
        value = master_key or get_settings().require_credential_master_key()
        return value.encode("utf-8")

    def _derive_key(self, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=AES_KEY_BYTES,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(self._master_key)

    def _parse_payload(self, encrypted_payload: str) -> tuple[str, bytes, bytes, bytes]:
        parts = encrypted_payload.split(":")
        if len(parts) != 4:
            raise ConfigurationError("Malformed credential encryption payload")
        version, salt, nonce, cipher_text = parts
        return (
            version,
            _urlsafe_b64decode(salt),
            _urlsafe_b64decode(nonce),
            _urlsafe_b64decode(cipher_text),
        )


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8")


def _urlsafe_b64decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value.encode("utf-8"))
    except Exception as exc:  # pragma: no cover
        raise ConfigurationError("Malformed credential encryption payload") from exc
