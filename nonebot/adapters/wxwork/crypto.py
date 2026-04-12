import base64
import hashlib
import os
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .exception import ActionFailed


def _compute_signature(token: str, timestamp: str, nonce: str, msg_encrypt: str) -> str:
    parts = sorted([token, timestamp, nonce, msg_encrypt])

    return hashlib.sha1("".join(parts).encode()).hexdigest()


class WxBizMsgCrypt:
    def __init__(self, token: str, encoding_aes_key: str, receive_id: str) -> None:
        self.token = token
        self.receive_id = receive_id
        self.aes_key = base64.b64decode(encoding_aes_key + "=")
        assert len(self.aes_key) == 32, "AESKey must be 32 bytes"
        self.iv = self.aes_key[:16]

    def verify_signature(
        self, msg_signature: str, timestamp: str, nonce: str, msg_encrypt: str
    ) -> bool:
        expected = _compute_signature(self.token, timestamp, nonce, msg_encrypt)

        return expected == msg_signature

    def _pkcs7_unpad(self, data: bytes) -> bytes:
        pad_len = data[-1]

        return data[:-pad_len]

    def _pkcs7_pad(self, data: bytes, block_size: int = 32) -> bytes:
        pad_len = block_size - (len(data) % block_size)

        return data + bytes([pad_len] * pad_len)

    def decrypt(self, msg_encrypt: str) -> str:
        aes_msg = base64.b64decode(msg_encrypt)
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.iv))
        decryptor = cipher.decryptor()
        rand_msg = decryptor.update(aes_msg) + decryptor.finalize()
        rand_msg = self._pkcs7_unpad(rand_msg)
        # 去掉前 16 字节随机串
        content = rand_msg[16:]
        # 取 4 字节 msg_len（big-endian）
        msg_len = struct.unpack(">I", content[:4])[0]
        # 取 msg
        msg = content[4 : 4 + msg_len]

        return msg.decode("utf-8")

    def encrypt(self, msg: str, timestamp: str, nonce: str) -> dict[str, str]:
        msg_bytes = msg.encode("utf-8")
        random_bytes = os.urandom(16)
        msg_len_bytes = struct.pack(">I", len(msg_bytes))
        receive_id_bytes = self.receive_id.encode("utf-8")
        plain = random_bytes + msg_len_bytes + msg_bytes + receive_id_bytes
        padded = self._pkcs7_pad(plain)
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.iv))
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded) + encryptor.finalize()
        msg_encrypt = base64.b64encode(encrypted).decode("utf-8")
        msg_signature = _compute_signature(self.token, timestamp, nonce, msg_encrypt)

        return {
            "Encrypt": msg_encrypt,
            "MsgSignature": msg_signature,
            "TimeStamp": timestamp,
            "Nonce": nonce,
        }

    def verify_url(
        self, msg_signature: str, timestamp: str, nonce: str, echostr: str
    ) -> str:
        if not self.verify_signature(msg_signature, timestamp, nonce, echostr):
            raise ActionFailed(errcode=-1, errmsg="invalid signature")

        return self.decrypt(echostr)
