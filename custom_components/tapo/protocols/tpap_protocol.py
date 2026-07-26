"""Implementation of the TP-Link TPAP (TP-Link Authentication Protocol).

Ported from python-kasa PR #1592 and adapted for plugp100's TapoProtocol interface.
Uses PAKE (Password-Authenticated Key Exchange) with elliptic curve cryptography.
"""
import asyncio
import base64
import hashlib
import hmac
import logging
import secrets
import struct
from typing import Any, Optional, TYPE_CHECKING

import aiohttp
import jsons
from aiohttp import ClientSession
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESCCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.cmac import CMAC
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography import x509
from ecdsa import NIST256p, NIST384p, NIST521p, ellipticcurve
from passlib.hash import md5_crypt, sha256_crypt
from yarl import URL

# Import plugp100 base classes
from plugp100.common.credentials import AuthCredential
from plugp100.common.functional.tri import Try, Failure, Success
from plugp100.api.protocol.tapo_protocol import TapoProtocol
from plugp100.api.requests.tapo_request import TapoRequest
from plugp100.api.transport.response import TapoResponse
from plugp100.api.transport.exceptions import TapoException, TapoError

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ecdsa.curves import Curve
    from ecdsa.ellipticcurve import CurveFp, PointJacobi


# ─────────────────────────────────────────────────────
# Crypto helpers
# ─────────────────────────────────────────────────────

TAG_LEN = 16
NONCE_LEN = 12

CIPHER_PARAMETERS: dict[str, tuple[bytes, bytes, bytes, bytes, int]] = {
    "aes_128_ccm": (
        b"tp-kdf-salt-aes128-key",
        b"tp-kdf-info-aes128-key",
        b"tp-kdf-salt-aes128-iv",
        b"tp-kdf-info-aes128-iv",
        16,
    ),
    "aes_256_ccm": (
        b"tp-kdf-salt-aes256-key",
        b"tp-kdf-info-aes256-key",
        b"tp-kdf-salt-aes256-iv",
        b"tp-kdf-info-aes256-iv",
        32,
    ),
    "chacha20_poly1305": (
        b"tp-kdf-salt-chacha20-key",
        b"tp-kdf-info-chacha20-key",
        b"tp-kdf-salt-chacha20-iv",
        b"tp-kdf-info-chacha20-iv",
        32,
    ),
}


def _md5_hex(value: str) -> str:
    return hashlib.md5(value.encode()).hexdigest()


def _sha256_hex_upper(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest().upper()


def _sha1_hex(value: str) -> str:
    return hashlib.sha1(value.encode()).hexdigest()


def _base64(value: bytes) -> str:
    return base64.b64encode(value).decode()


def _unbase64(value: str) -> bytes:
    return base64.b64decode(value)


def _hash(algorithm: str, data: bytes) -> bytes:
    if algorithm.upper() == "SHA512":
        return hashlib.sha512(data).digest()
    return hashlib.sha256(data).digest()


def _hkdf_expand(label: str, prk: bytes, digest_len: int, algorithm: str) -> bytes:
    hkdf_algo = hashes.SHA512() if algorithm.upper() == "SHA512" else hashes.SHA256()
    return HKDF(
        algorithm=hkdf_algo,
        length=digest_len,
        salt=b"\x00" * digest_len,
        info=label.encode(),
    ).derive(prk)


def _hkdf(master: bytes, *, salt: bytes, info: bytes, length: int, algo: str = "SHA256") -> bytes:
    algorithm = hashes.SHA256() if algo.upper() == "SHA256" else hashes.SHA512()
    return HKDF(algorithm=algorithm, length=length, salt=salt, info=info).derive(master)


def _hmac(algorithm: str, key: bytes, data: bytes) -> bytes:
    digest = hashlib.sha512 if algorithm.upper() == "SHA512" else hashlib.sha256
    return hmac.new(key, data, digest).digest()


def _cmac_aes(key: bytes, data: bytes) -> bytes:
    cmac = CMAC(algorithms.AES(key))
    cmac.update(data)
    return cmac.finalize()


def _pbkdf2_sha256(password: bytes, salt: bytes, iterations: int, length: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password, salt, iterations, length)


def _sec1_to_xy(sec1: bytes, curve) -> tuple[int, int]:
    public_key = ec.EllipticCurvePublicKey.from_encoded_point(curve, sec1)
    numbers = public_key.public_numbers()
    return numbers.x, numbers.y


def _xy_to_uncompressed(x: int, y: int, curve) -> bytes:
    numbers = ec.EllipticCurvePublicNumbers(x, y, curve)
    public_key = numbers.public_key()
    return public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )


def _len8le(value: bytes) -> bytes:
    return len(value).to_bytes(8, "little") + value


def _encode_w(value: int) -> bytes:
    minimal_length = 1 if value == 0 else (value.bit_length() + 7) // 8
    unsigned = value.to_bytes(minimal_length, "big", signed=False)
    if minimal_length % 2 == 0:
        return unsigned
    if unsigned[0] & 0x80:
        return b"\x00" + unsigned
    return unsigned


def _derive_ab(credentials: bytes, salt: bytes, iterations: int, hash_len: int = 32) -> tuple[int, int]:
    i_d = hash_len + 8
    derived = _pbkdf2_sha256(credentials, salt, iterations, 2 * i_d)
    return (
        int.from_bytes(derived[:i_d], "big"),
        int.from_bytes(derived[i_d:], "big"),
    )


def _nonce_from_base(base_nonce: bytes, seq: int) -> bytes:
    if len(base_nonce) < 4:
        raise ValueError("base nonce too short")
    return base_nonce[:-4] + struct.pack(">I", seq)


def _suite_hash_name(suite_type: int) -> str:
    return "SHA512" if suite_type in (2, 4, 5, 7, 9) else "SHA256"


def _suite_mac_is_cmac(suite_type: int) -> bool:
    return suite_type in (8, 9)


def _suite_parameters(suite_type: int) -> tuple[bytes, bytes, "Curve", ec.EllipticCurve]:
    if suite_type in (1, 2, 8, 9):
        return (
            bytes.fromhex("02886e2f97ace46e55ba9dd7242579f2993b64e16ef3dcab95afd497333d8fa12f"),
            bytes.fromhex("03d8bbd6c639c62937b04d997f38c3770719c629d7014d49a24b4f98baa1292b49"),
            NIST256p,
            ec.SECP256R1(),
        )
    if suite_type in (3, 4):
        return (
            bytes.fromhex("030ff0895ae5ebf6187080a82d82b42e2765e3b2f8749c7e05eba366434b363d3dc36f15314739074d2eb8613fceec2853"),
            bytes.fromhex("02c72cf2e390853a1c1c4ad816a62fd15824f56078918f43f922ca21518f9c543bb252c5490214cf9aa3f0baab4b665c10"),
            NIST384p,
            ec.SECP384R1(),
        )
    if suite_type == 5:
        return (
            bytes.fromhex("02003f06f38131b2ba2600791e82488e8d20ab889af753a41806c5db18d37d85608cfae06b82e4a72cd744c719193562a653ea1f119eef9356907edc9b56979962d7aa"),
            bytes.fromhex("0200c7924b9ec017f3094562894336a53c50167ba8c5963876880542bc669e494b2532d76c5b53dfb349fdf69154b9e0048c58a42e8ed04cef052a3bc349d95575cd25"),
            NIST521p,
            ec.SECP521R1(),
        )
    raise Exception(f"Unsupported TPAP suite type: {suite_type}")


def _normalize_cipher_id(cipher_id: str) -> str:
    return cipher_id.lower().replace("-", "_")


def _encrypt_payload(cipher_id: str, key: bytes, base_nonce: bytes, plaintext: bytes, seq: int) -> bytes:
    nonce = _nonce_from_base(base_nonce, seq)
    normalized = _normalize_cipher_id(cipher_id)
    if normalized.startswith("aes_"):
        return AESCCM(key, tag_length=TAG_LEN).encrypt(nonce, plaintext, None)
    return ChaCha20Poly1305(key).encrypt(nonce, plaintext, None)


def _decrypt_payload(cipher_id: str, key: bytes, base_nonce: bytes, ciphertext_and_tag: bytes, seq: int) -> bytes:
    nonce = _nonce_from_base(base_nonce, seq)
    normalized = _normalize_cipher_id(cipher_id)
    if normalized.startswith("aes_"):
        return AESCCM(key, tag_length=TAG_LEN).decrypt(nonce, ciphertext_and_tag, None)
    return ChaCha20Poly1305(key).decrypt(nonce, ciphertext_and_tag, None)


def _mac_pass_from_device_mac(mac_colon: str) -> str:
    mac_hex = mac_colon.replace(":", "").replace("-", "")
    try:
        mac_bytes = bytes.fromhex(mac_hex)
    except ValueError as exc:
        raise Exception("Invalid device MAC for TPAP default passcode") from exc
    if len(mac_bytes) < 6:
        raise Exception("Device MAC too short for TPAP default passcode")
    seed = b"GqY5o136oa4i6VprTlMW2DpVXxmfW8"
    ikm = seed + mac_bytes[3:6] + mac_bytes[0:3]
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"tp-kdf-salt-default-passcode",
        info=b"tp-kdf-info-default-passcode",
    ).derive(ikm).hex().upper()


def _build_credentials(extra_crypt: Optional[dict], username: str, passcode: str, mac_no_colon: str) -> str:
    if not extra_crypt:
        return f"{username}/{passcode}" if username else passcode
    crypt_type = (extra_crypt.get("type") or "").lower()
    params = extra_crypt.get("params")
    if not isinstance(params, dict):
        params = {}
    if crypt_type == "password_shadow":
        try:
            passwd_id = int(params.get("passwd_id", 0))
        except (TypeError, ValueError):
            return passcode
        prefix = str(params.get("passwd_prefix", "") or "")
        if passwd_id == 1:
            return md5_crypt.using(salt=prefix[:8]).hash(passcode) or passcode
        if passwd_id == 2:
            return _sha1_hex(passcode)
        if passwd_id == 3:
            return _sha1_username_mac_shadow(username, mac_no_colon, passcode)
        if passwd_id == 5:
            return _sha256_crypt(passcode, prefix, params.get("passwd_rounds")) or passcode
        return passcode
    if crypt_type == "password_authkey":
        tmpkey = str(params.get("authkey_tmpkey", "") or "")
        dictionary = str(params.get("authkey_dictionary", "") or "")
        if tmpkey and dictionary:
            return _authkey_mask(passcode, tmpkey, dictionary)
        return passcode
    if crypt_type == "password_sha_with_salt":
        try:
            sha_name = int(params.get("sha_name", -1))
        except (TypeError, ValueError):
            return passcode
        sha_salt_b64 = str(params.get("sha_salt", "") or "")
        username_hint = "admin" if sha_name == 0 else "user"
        try:
            decoded_salt = base64.b64decode(sha_salt_b64).decode()
        except Exception:
            return passcode
        return hashlib.sha256(
            (username_hint + decoded_salt + passcode).encode()
        ).hexdigest()
    return f"{username}/{passcode}" if username else passcode


def _authkey_mask(passcode: str, tmpkey: str, dictionary: str) -> str:
    masked = []
    max_length = max(len(tmpkey), len(passcode))
    for index in range(max_length):
        lhs = ord(passcode[index]) if index < len(passcode) else 0xBB
        rhs = ord(tmpkey[index]) if index < len(tmpkey) else 0xBB
        masked.append(dictionary[(lhs ^ rhs) % len(dictionary)])
    return "".join(masked)


def _sha1_username_mac_shadow(username: str, mac12hex: str, password: str) -> str:
    if not username or len(mac12hex) != 12 or not all(
        char in "0123456789abcdefABCDEF" for char in mac12hex
    ):
        return password
    mac = ":".join(mac12hex[index : index + 2] for index in range(0, 12, 2)).upper()
    return _sha1_hex(_md5_hex(username) + "_" + mac)


def _sha256_crypt(password: str, prefix: str, rounds_from_params: int | None = None) -> Optional[str]:
    if not prefix:
        return None
    default_rounds = 5000
    min_rounds = 1000
    max_rounds = 999_999_999
    spec = prefix[3:] if prefix.startswith("$5$") else prefix
    rounds: int | None = None
    if spec.startswith("rounds="):
        rounds_part, _, salt_part = spec.partition("$")
        try:
            rounds = int(rounds_part.split("=", 1)[1])
        except ValueError:
            rounds = default_rounds
        rounds = max(min_rounds, min(max_rounds, rounds))
        salt = salt_part
    else:
        salt = spec.split("$", 1)[0] if "$" in spec else spec
    if rounds_from_params is not None:
        try:
            parsed_rounds = int(rounds_from_params)
        except (TypeError, ValueError):
            parsed_rounds = default_rounds
        rounds = max(min_rounds, min(max_rounds, parsed_rounds))
    salt = salt[:16]
    if rounds is not None:
        return sha256_crypt.using(rounds=rounds, salt=salt).hash(password)
    return sha256_crypt.using(salt=salt).hash(password)


# ─────────────────────────────────────────────────────
# TpapEncryptionSession - stateful session for TPAP
# ─────────────────────────────────────────────────────

class TpapEncryptionSession:
    """Manages a TPAP encryption session with a device."""

    PAKE_CONTEXT_TAG = b"PAKE V1"

    def __init__(self, transport: "TpapProtocol"):
        self._transport = transport
        self._handshake_lock = asyncio.Lock()
        self._device_mac: str = ""
        self._tpap_tls: Optional[int] = None
        self._tpap_port: Optional[int] = None
        self._tpap_dac: bool = False
        self._tpap_pake: list[int] = []
        self._tpap_user_hash_type: Optional[int] = None
        self._session_id: Optional[str] = None
        self._sequence: Optional[int] = None
        self._ds_url: Optional[URL] = None
        self._cipher_id: str = "aes_128_ccm"
        self._hkdf_hash: str = "SHA256"
        self._key: Optional[bytes] = None
        self._base_nonce: Optional[bytes] = None
        self._shared_key: Optional[bytes] = None
        self._expected_dev_confirm: Optional[str] = None
        self._dac_nonce_base64: Optional[str] = None
        self._user_random: Optional[str] = None
        self.reset()

    @property
    def is_established(self) -> bool:
        return (
            self._session_id is not None
            and self._sequence is not None
            and self._ds_url is not None
            and self._key is not None
            and self._base_nonce is not None
        )

    def _invalidate_session(self) -> None:
        self._session_id = None
        self._sequence = None
        self._ds_url = None
        self._cipher_id = "aes_128_ccm"
        self._hkdf_hash = "SHA256"
        self._key = None
        self._base_nonce = None
        self._shared_key = None
        self._expected_dev_confirm = None
        self._dac_nonce_base64 = None
        self._user_random = None

    def reset(self) -> None:
        self._device_mac = self._transport._known_device_mac
        self._tpap_tls = self._transport._known_tpap_tls
        self._tpap_port = self._transport._known_tpap_port
        self._tpap_dac = self._transport._known_tpap_dac
        self._tpap_pake = list(self._transport._known_tpap_pake)
        self._tpap_user_hash_type = self._transport._known_tpap_user_hash_type
        self._invalidate_session()

    def _update_transport_url(self) -> None:
        self._transport._app_url = self._transport._build_app_url(
            tls_mode=self._tpap_tls,
            port=self._tpap_port,
        )

    @staticmethod
    def _parse_optional_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _require_result_dict(response: dict) -> dict:
        result = response.get("result")
        if not isinstance(result, dict):
            raise Exception("TPAP response missing result object")
        return result

    async def _login(self, params: dict, *, step_name: str) -> dict:
        body = {"method": "login", "params": params}
        status, data = await self._transport._http_post(
            self._transport._app_url.with_path("/"),
            json=body,
        )
        if status != 200 or not isinstance(data, dict):
            raise Exception(
                f"TPAP {step_name} failed for {self._transport._host}: "
                f"{status} {type(data)}"
            )
        self._handle_response_error_code(data, step_name)
        return self._require_result_dict(data)

    def _handle_response_error_code(self, response: dict, action: str) -> None:
        error_code_raw = response.get("error_code")
        if error_code_raw == 0:
            return

        full = f"TPAP {action} failed for {self._transport._host}: {error_code_raw}"
        # Error 1003 = invalid JSON/auth
        if error_code_raw == 1003:
            self._invalidate_session()
            raise Exception(f"{full} (invalid auth)")
        # Error -1501 = INVALID_CREDENTIAL
        if error_code_raw == -1501:
            self._invalidate_session()
            raise Exception(f"{full} (invalid credentials)")
        # Error 1111 = LOGIN_FAILED
        if error_code_raw == 1111:
            self._invalidate_session()
            raise Exception(f"{full} (login failed)")
        raise Exception(full)

    def _get_register_username(self) -> str:
        if self._tpap_user_hash_type == 1:
            return _sha256_hex_upper("admin")
        return _md5_hex("admin")

    def _get_passcode_type(self) -> Optional[str]:
        # For non-camera, non-robot devices, default to default_userpw
        passcode_type_order = (
            ((0,), "default_userpw"),
            ((2, 5), "userpw"),
            ((3,), "shared_token"),
        )
        pake = set(self._tpap_pake)
        for pake_values, passcode_type in passcode_type_order:
            if pake.intersection(pake_values):
                return passcode_type
        return "default_userpw"

    def _get_candidate_secrets(self) -> list[str]:
        passcode_type = self._get_passcode_type()
        if passcode_type == "default_userpw":
            return [_mac_pass_from_device_mac(self._device_mac)] if self._device_mac else []
        creds = self._transport._credentials
        password = (creds.password if creds else "") or ""
        return [password]

    def _resolve_credentials(self, register_result: dict, candidate_secret: str) -> str:
        if self._get_passcode_type() == "default_userpw":
            return candidate_secret
        extra_crypt_value = register_result.get("extra_crypt")
        extra_crypt = extra_crypt_value if isinstance(extra_crypt_value, dict) else {}
        creds = self._transport._credentials
        username = (creds.username if creds else "") or ""
        mac_no_colon = self._device_mac.replace(":", "").replace("-", "")
        return _build_credentials(extra_crypt, username, candidate_secret, mac_no_colon)

    async def _discover(self) -> None:
        body = {"method": "login", "params": {"sub_method": "discover"}}
        status, data = await self._transport._http_post(
            self._transport._app_url.with_path("/"),
            json=body,
        )
        if status != 200 or not isinstance(data, dict):
            raise Exception(
                f"TPAP discover failed for {self._transport._host}: "
                f"{status} {type(data)}"
            )
        self._handle_response_error_code(data, "discover")
        result = self._require_result_dict(data)
        tpap = result.get("tpap")
        if not isinstance(tpap, dict):
            raise Exception("TPAP discover response missing tpap object")
        self._device_mac = str(result.get("mac") or "")
        self._tpap_tls = self._parse_optional_int(tpap.get("tls"))
        self._tpap_port = self._parse_optional_int(tpap.get("port"))
        self._tpap_dac = bool(tpap.get("dac"))
        self._tpap_pake = list(tpap.get("pake") or [])
        self._tpap_user_hash_type = self._parse_optional_int(tpap.get("user_hash_type"))
        self._transport._known_device_mac = self._device_mac
        self._transport._known_tpap_tls = self._tpap_tls
        self._transport._known_tpap_port = self._tpap_port
        self._transport._known_tpap_dac = self._tpap_dac
        self._transport._known_tpap_pake = list(self._tpap_pake)
        self._transport._known_tpap_user_hash_type = self._tpap_user_hash_type
        self._update_transport_url()

    async def _perform_auth_handshake(self) -> None:
        passcode_type = self._get_passcode_type()
        if passcode_type is None:
            raise Exception(f"TPAP: no supported passcode type for {self._transport._host}")
        candidate_secrets = self._get_candidate_secrets()
        if not candidate_secrets:
            raise Exception(f"TPAP: no credential candidates for {self._transport._host}")

        register_username = self._get_register_username()
        last_error = None

        for attempt, candidate_secret in enumerate(candidate_secrets, start=1):
            self._shared_key = None
            self._expected_dev_confirm = None
            self._dac_nonce_base64 = None
            self._user_random = _base64(secrets.token_bytes(32))

            register_params = {
                "sub_method": "pake_register",
                "username": register_username,
                "user_random": self._user_random,
                "cipher_suites": [1],
                "encryption": ["aes_128_ccm"],
                "passcode_type": passcode_type,
                "stok": None,
            }
            try:
                register_result = await self._login(register_params, step_name="pake_register")
                credentials_string = self._resolve_credentials(register_result, candidate_secret)
                share_params = self._build_share_params_from_register(register_result, credentials_string)
                if self._use_dac_certification():
                    self._dac_nonce_base64 = _base64(secrets.token_bytes(32))
                    share_params["dac_nonce"] = self._dac_nonce_base64
                share_result = await self._login(share_params, step_name="pake_share")
                self._establish_session_from_share_result(share_result)
                return
            except Exception as exc:
                last_error = exc
                if attempt < len(candidate_secrets):
                    _LOGGER.debug(
                        "TPAP: credential candidate %d/%d failed for %s: %s",
                        attempt, len(candidate_secrets), self._transport._host, exc,
                    )

        raise last_error or Exception("TPAP: handshake did not produce a session")

    def _use_dac_certification(self) -> bool:
        return self._tpap_tls == 0 and self._tpap_dac

    def _build_share_params_from_register(
        self, register_result: dict, credentials_string: str
    ) -> dict:
        if self._user_random is None:
            raise Exception("TPAP user random not initialized")
        dev_random = str(register_result.get("dev_random") or "")
        dev_salt = str(register_result.get("dev_salt") or "")
        dev_share = str(register_result.get("dev_share") or "")
        for field, value in (("dev_random", dev_random), ("dev_salt", dev_salt), ("dev_share", dev_share)):
            if not value:
                raise Exception(f"TPAP register response missing {field}")

        suite_type = int(register_result["cipher_suites"])
        iterations = int(register_result["iterations"])
        encryption = str(register_result.get("encryption") or "")
        if not encryption:
            raise Exception("TPAP register response missing encryption")

        chosen_cipher = _normalize_cipher_id(encryption)
        if chosen_cipher not in CIPHER_PARAMETERS:
            raise Exception(f"Unsupported TPAP cipher: {encryption}")
        self._cipher_id = chosen_cipher
        self._hkdf_hash = _suite_hash_name(suite_type)

        m_comp, n_comp, nist, crypto_curve = _suite_parameters(suite_type)
        curve: "CurveFp" = nist.curve
        generator: "PointJacobi" = nist.generator
        order = generator.order()
        g_point = generator

        m_x, m_y = _sec1_to_xy(m_comp, crypto_curve)
        n_x, n_y = _sec1_to_xy(n_comp, crypto_curve)
        m_point = ellipticcurve.Point(curve, m_x, m_y, order)
        n_point = ellipticcurve.Point(curve, n_x, n_y, order)

        credential_bytes = credentials_string.encode()
        a_value, b_value = _derive_ab(credential_bytes, _unbase64(dev_salt), iterations, 32)
        w_value = a_value % order
        h_value = b_value % order
        x_value = secrets.randbelow(order - 1) + 1

        l_point = x_value * g_point + w_value * m_point
        l_encoded = _xy_to_uncompressed(l_point.x(), l_point.y(), crypto_curve)

        device_share_bytes = _unbase64(dev_share)
        r_x, r_y = _sec1_to_xy(device_share_bytes, crypto_curve)
        r_point = ellipticcurve.Point(curve, r_x, r_y, order)
        r_encoded = _xy_to_uncompressed(r_point.x(), r_point.y(), crypto_curve)

        r_prime = r_point + (-(w_value * n_point))
        z_point = x_value * r_prime
        v_point = (h_value % order) * r_prime

        z_encoded = _xy_to_uncompressed(z_point.x(), z_point.y(), crypto_curve)
        v_encoded = _xy_to_uncompressed(v_point.x(), v_point.y(), crypto_curve)
        m_encoded = _xy_to_uncompressed(m_point.x(), m_point.y(), crypto_curve)
        n_encoded = _xy_to_uncompressed(n_point.x(), n_point.y(), crypto_curve)

        context_hash = _hash(
            self._hkdf_hash,
            self.PAKE_CONTEXT_TAG
            + _unbase64(self._user_random)
            + _unbase64(dev_random),
        )
        w_encoded = _encode_w(w_value)
        transcript = (
            _len8le(context_hash)
            + _len8le(b"")
            + _len8le(b"")
            + _len8le(m_encoded)
            + _len8le(n_encoded)
            + _len8le(l_encoded)
            + _len8le(r_encoded)
            + _len8le(z_encoded)
            + _len8le(v_encoded)
            + _len8le(w_encoded)
        )
        transcript_hash = _hash(self._hkdf_hash, transcript)

        digest_len = 64 if self._hkdf_hash.upper() == "SHA512" else 32
        mac_len = 16 if _suite_mac_is_cmac(suite_type) else 32

        confirmation_keys = _hkdf_expand(
            "ConfirmationKeys", transcript_hash, mac_len * 2, self._hkdf_hash
        )
        key_confirm_a = confirmation_keys[:mac_len]
        key_confirm_b = confirmation_keys[mac_len : mac_len * 2]

        self._shared_key = _hkdf_expand(
            "SharedKey", transcript_hash, digest_len, self._hkdf_hash
        )

        if _suite_mac_is_cmac(suite_type):
            user_confirm = _cmac_aes(key_confirm_a, r_encoded)
            expected_dev_confirm = _cmac_aes(key_confirm_b, l_encoded)
        else:
            user_confirm = _hmac(self._hkdf_hash, key_confirm_a, r_encoded)
            expected_dev_confirm = _hmac(self._hkdf_hash, key_confirm_b, l_encoded)

        self._expected_dev_confirm = _base64(expected_dev_confirm)

        return {
            "sub_method": "pake_share",
            "user_share": _base64(l_encoded),
            "user_confirm": _base64(user_confirm),
        }

    def _establish_session_from_share_result(self, share_result: dict) -> None:
        dev_confirm = str(share_result.get("dev_confirm") or "").lower()
        if not dev_confirm:
            raise Exception("TPAP share response missing dev_confirm")
        if dev_confirm != (self._expected_dev_confirm or "").lower():
            raise Exception("TPAP confirmation mismatch")

        session_id = str(share_result.get("sessionId") or share_result.get("stok") or "")
        if not session_id:
            raise Exception("TPAP: missing session ID from device")
        if self._shared_key is None:
            raise Exception("TPAP shared key was not derived")

        start_seq = share_result.get("start_seq")
        if start_seq is None:
            raise Exception("TPAP: missing start_seq from device")
        sequence = int(start_seq)

        key_salt, key_info, nonce_salt, nonce_info, key_len = CIPHER_PARAMETERS[
            _normalize_cipher_id(self._cipher_id)
        ]
        self._key = _hkdf(
            self._shared_key,
            salt=key_salt,
            info=key_info,
            length=key_len,
            algo=self._hkdf_hash,
        )
        self._base_nonce = _hkdf(
            self._shared_key,
            salt=nonce_salt,
            info=nonce_info,
            length=NONCE_LEN,
            algo=self._hkdf_hash,
        )
        self._session_id = session_id
        self._sequence = sequence
        self._ds_url = URL(f"{self._transport._app_url}/stok={self._session_id}/ds")

    async def perform_handshake(self) -> None:
        async with self._handshake_lock:
            if self.is_established:
                return
            self.reset()
            _LOGGER.debug("TPAP: starting handshake with %s", self._transport._host)
            await self._discover()
            await self._perform_auth_handshake()
            _LOGGER.debug("TPAP: handshake complete with %s", self._transport._host)

    def encrypt(self, payload: bytes | str) -> tuple[bytes, int]:
        """Encrypt payload, return (encrypted_bytes_with_header, seq)."""
        cipher_id = self._cipher_id
        key = self._key
        base_nonce = self._base_nonce
        seq = self._sequence
        if seq is None or key is None or base_nonce is None:
            raise Exception("TPAP session not established for encryption")
        plaintext = payload.encode() if isinstance(payload, str) else payload
        encrypted = _encrypt_payload(cipher_id, key, base_nonce, plaintext, seq)
        self._sequence = seq + 1
        return struct.pack(">I", seq) + encrypted, seq

    def decrypt(self, payload: bytes, request_seq: int) -> bytes:
        """Decrypt payload and return plaintext bytes."""
        cipher_id = self._cipher_id
        key = self._key
        base_nonce = self._base_nonce
        if key is None or base_nonce is None:
            raise Exception("TPAP session not established for decryption")
        if len(payload) < 4 + TAG_LEN:
            raise Exception("TPAP response too short")
        response_seq = struct.unpack(">I", payload[:4])[0]
        if response_seq != request_seq:
            _LOGGER.debug("TPAP device returned rseq %d (expected %d)", response_seq, request_seq)
        return _decrypt_payload(cipher_id, key, base_nonce, payload[4:], response_seq)


# ─────────────────────────────────────────────────────
# TpapProtocol - plugp100 TapoProtocol implementation
# ─────────────────────────────────────────────────────

TPAP_ROOT_CA_PEM = """\
-----BEGIN CERTIFICATE-----
MIICNzCCAdygAwIBAgIUNLD7w5j5WU/efCe8bqkfGSRGgLYwCgYIKoZIzj0EAwIw
ezEnMCUGA1UEAwweVFAtTElOSyBTWVNURU1TIERFVklURSBSRU9UIENBMR0wGwYD
VQQKDBRUUC1MSU5LIFNZU1RFTVMgSU5DLjEPMA0GA1UEBwwGSXJ2aW5lMRMwEQYD
VQQIDApDYWxpZm9ybmlhMQswCQYDVQQGEwJVUzAgFw0yNDExMjIwMjU3NDhaGA8y
MDU0MTExNTAyNTc0OFowezEnMCUGA1UEAwweVFAtTElOSyBTWVNURU1TIERFVklD
RSBST09UIENBMR0wGwYDVQQKDBRUUC1MSU5LIFNZU1RFTVMgSU5DLjEPMA0GA1UE
BwwGSXJ2aW5lMRMwEQYDVQQIDApDYWxpZm9ybmlhMQswCQYDVQQGEwJVUzBZMBMG
ByqGSM49AgEGCCqGSM49AwEHA0IABLwo8H9H6BoJDvcoewi4wPrPryVXir4z4yXV
n29R5XCAcFfKk06pYPupG6pjaKOLKWXnaOdPZThDFxwGLo3urV2jPDA6MAsGA1Ud
DwQEAwIBhjAMBgNVHRMEBTADAQH/MB0GA1UdDgQWBBRivfUtiHYsZBOKo80uZEwk
XhBkdDAKBggqhkjOPQQDAgNJADBGAiEA+7j5jemtXcGYN0unH+9rjVhVAL7WrsOi
5rbc0IIvD6MCIQCZuGGssu4Ygt2V8Vr0QF2fO9wxfNB3aRRMYQ+6lMrLGA==
-----END CERTIFICATE-----
""".strip()


class TpapProtocol(TapoProtocol):
    """TP-Link TPAP protocol implementation.

    Uses PAKE (Password-Authenticated Key Exchange) for authentication
    and AES-CCM encryption for payload protection.
    """

    DEFAULT_PORT = 80
    DEFAULT_HTTPS_PORT = 4433
    COMMON_HEADERS = {"Content-Type": "application/json"}

    def __init__(
        self,
        auth_credential: AuthCredential,
        url: str,
        http_session: Optional[ClientSession] = None,
        *,
        initial_tpap_port: Optional[int] = None,
        initial_tpap_tls: Optional[int] = None,
        initial_device_mac: str = "",
    ):
        self._credentials = auth_credential
        self._http_session: Optional[ClientSession] = http_session
        self._owns_http_session = http_session is None

        # Parse the URL to get host and port
        if url.startswith("http://") or url.startswith("https://"):
            parsed = URL(url)
            self._host = parsed.host or url.split("://")[1].split(":")[0]
            port = parsed.port or self.DEFAULT_PORT
        else:
            self._host = url.split(":")[0]
            port = int(url.split(":")[1]) if ":" in url else self.DEFAULT_PORT

        protocol = "https" if initial_tpap_tls in (1, 2) else "http"
        if initial_tpap_port and initial_tpap_port > 0:
            resolved_port = initial_tpap_port
        elif protocol == "https":
            resolved_port = self.DEFAULT_HTTPS_PORT
        else:
            resolved_port = port

        self._app_url = URL.build(scheme=protocol, host=self._host, port=resolved_port)
        self._bootstrap_url = URL.build(scheme=protocol, host=self._host, port=port)

        self._known_device_mac = initial_device_mac
        self._known_tpap_tls: Optional[int] = initial_tpap_tls
        self._known_tpap_port: Optional[int] = initial_tpap_port
        self._known_tpap_dac = False
        self._known_tpap_pake: list[int] = []
        self._known_tpap_user_hash_type: Optional[int] = None

        self._send_lock = asyncio.Lock()
        self._encryption_session = TpapEncryptionSession(self)

    def _build_app_url(self, *, tls_mode: Optional[int], port: Optional[int]) -> URL:
        scheme = "https" if tls_mode in (1, 2) else "http"
        if port and port > 0:
            resolved_port = port
        elif scheme == "https":
            resolved_port = self.DEFAULT_HTTPS_PORT
        else:
            resolved_port = self.DEFAULT_PORT
        return URL.build(scheme=scheme, host=self._host, port=resolved_port)

    @property
    def name(self) -> str:
        return "TPAP"

    async def _http_post(self, url: URL, *, json=None, data=None, headers=None) -> tuple[int, Any]:
        """Post HTTP request and return (status_code, parsed_data)."""
        if self._http_session is None:
            self._http_session = ClientSession(
                cookie_jar=aiohttp.CookieJar(unsafe=True, quote_cookie=False)
            )
            self._owns_http_session = True

        headers = headers or self.COMMON_HEADERS
        try:
            async with self._http_session.post(url, json=json, data=data, headers=headers) as resp:
                status = resp.status
                raw = await resp.read()
                if status != 200:
                    _LOGGER.warning("TPAP HTTP %d from %s: %s", status, self._host, raw[:200])
                try:
                    return status, (await resp.json())
                except Exception:
                    return status, raw
        except asyncio.TimeoutError:
            raise Exception(f"TPAP request timeout to {self._host}")

    async def send_request(
        self, request: TapoRequest, retry: int = 3
    ) -> Try[TapoResponse[dict[str, Any]]]:
        """Send a request using TPAP encrypted transport."""
        try:
            result = await self._send_request_once(request, retry)
            # Check if the response contains a session expiry error
            if isinstance(result, Failure):
                return result
            if isinstance(result, Success) and result.value is not None and result.value.error_code == -40421:
                # Session expired, re-handshake and retry
                if retry > 0:
                    self._encryption_session.reset()
                    return await self.send_request(request, retry - 1)
            return result
        except Exception as e:
            if retry > 0:
                try:
                    self._encryption_session.reset()
                    return await self._send_request_once(request, retry - 1)
                except Exception:
                    pass
            return Failure(e)

    async def _send_request_once(
        self, request: TapoRequest, retry: int = 1
    ) -> Try[TapoResponse[dict[str, Any]]]:
        # Ensure handshake is done
        if not self._encryption_session.is_established:
            await self._encryption_session.perform_handshake()

        ds_url = self._encryption_session._ds_url
        if ds_url is None:
            return Failure(Exception("TPAP transport not established"))

        async with self._send_lock:
            # Serialize the request to JSON (jsons handles dataclass/obj serialization)
            raw_request = jsons.dumps(request)
            payload, seq = self._encryption_session.encrypt(raw_request)

            status, raw_response = await self._http_post(
                ds_url,
                data=payload,
                headers={"Content-Type": "application/octet-stream"},
            )
            if status == 401:
                raise Exception("TPAP session expired (401), re-handshake needed")
            if status != 200:
                return Failure(Exception(f"TPAP secure request failed: status {status}"))

            if isinstance(raw_response, bytes):
                raw_response = bytes(raw_response)

            plaintext = self._encryption_session.decrypt(raw_response, seq)
            if isinstance(plaintext, bytes):
                plaintext = plaintext.decode()

            try:
                import json as _json
                response_dict = _json.loads(plaintext)
            except Exception:
                return Failure(Exception(f"TPAP response parse failed: {plaintext[:100]}"))

            return TapoResponse.try_from_json(response_dict)

    async def close(self):
        """Close the transport."""
        self._encryption_session.reset()
        if self._owns_http_session and self._http_session:
            try:
                await self._http_session.close()
            except Exception:
                pass