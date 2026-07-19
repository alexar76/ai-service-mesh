"""Zero-trust agent verification — cryptographic and policy checks."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from ai_service_mesh.security import url_is_safe


@dataclass
class VerificationResult:
    ok: bool
    trust_score: float
    reasons: list[str]


def _load_public_key(pem: str):
    try:
        key = serialization.load_pem_public_key(pem.encode("utf-8"))
    except Exception:
        return None
    if not isinstance(key, (rsa.RSAPublicKey, ed25519.Ed25519PublicKey)):
        return None
    return key


def canonical_attestation_message(
    name: str, endpoint_url: str, capabilities: list[str]
) -> bytes:
    """Stable byte string an agent must sign to prove key ownership at registration."""
    return f"{name}|{endpoint_url}|{','.join(sorted(capabilities))}".encode("utf-8")


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def build_attestation(
    private_key, name: str, endpoint_url: str, capabilities: list[str]
) -> str:
    """Sign the canonical registration message with the agent's private key.

    SEC-03: attestation is a real signature (Ed25519 or RSA-PKCS1v15/SHA-256)
    over the canonical metadata, verifiable with the public key the agent
    submits — proving possession of the matching private key, not a guessable
    hash of public fields.
    """
    message = canonical_attestation_message(name, endpoint_url, capabilities)
    if isinstance(private_key, ed25519.Ed25519PrivateKey):
        sig = private_key.sign(message)
    elif isinstance(private_key, rsa.RSAPrivateKey):
        sig = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    else:
        raise TypeError("Unsupported private key type for attestation")
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def _attestation_signature_valid(key, message: bytes, attestation: str) -> bool:
    try:
        sig = _b64url_decode(attestation)
    except Exception:
        return False
    try:
        if isinstance(key, ed25519.Ed25519PublicKey):
            key.verify(sig, message)
            return True
        if isinstance(key, rsa.RSAPublicKey):
            key.verify(sig, message, padding.PKCS1v15(), hashes.SHA256())
            return True
    except InvalidSignature:
        return False
    except Exception:
        return False
    return False


def verify_agent_registration(
    *,
    name: str,
    endpoint_url: str,
    public_key_pem: str,
    capabilities: list[str],
    attestation: str,
    allow_localhost: bool = False,
) -> VerificationResult:
    reasons: list[str] = []
    score = 0.0

    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9 _\-\.]{1,118}[a-zA-Z0-9]$", name.strip()):
        reasons.append("invalid_name")
    else:
        score += 0.15

    if not url_is_safe(endpoint_url, allow_localhost=allow_localhost):
        reasons.append("unsafe_endpoint")
    else:
        score += 0.25

    key = _load_public_key(public_key_pem)
    if not key:
        reasons.append("invalid_public_key")
    else:
        score += 0.25

    if not capabilities or len(capabilities) > 32:
        reasons.append("invalid_capabilities")
    else:
        score += 0.15

    # SEC-03: require a cryptographic signature proving private-key possession.
    message = canonical_attestation_message(name, endpoint_url, capabilities)
    if not attestation:
        reasons.append("missing_attestation")
    elif key is None:
        reasons.append("invalid_attestation")
    elif _attestation_signature_valid(key, message, attestation):
        score += 0.2
    else:
        reasons.append("invalid_attestation")

    # Verified status (ok) now demands: safe endpoint, valid key, and a valid
    # attestation signature. A guessable/forged attestation no longer verifies.
    blocking = {
        "unsafe_endpoint",
        "invalid_public_key",
        "invalid_attestation",
        "missing_attestation",
    }
    ok = not blocking.intersection(reasons)
    return VerificationResult(ok=ok, trust_score=min(1.0, score), reasons=reasons)
