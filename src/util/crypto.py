import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def decrypt_string(encrypted_str: str, private_pem: str) -> str:
    if not encrypted_str or not private_pem:
        return ""
    try:
        encrypted_data = base64.b64decode(encrypted_str)
    except Exception:
        return ""
    try:
        decrypted_bytes = _decrypt_bytes(encrypted_data, private_pem)
        return decrypted_bytes.decode('utf-8', errors='ignore') if decrypted_bytes else ""
    except Exception:
        return ""

def _decrypt_bytes(encrypted_data: bytes, private_pem: str) -> bytes:
    private_key = serialization.load_pem_private_key(private_pem.encode('utf-8'), password=None)
    if encrypted_data[:1] == b'0':
        ciphertext = encrypted_data[1:]
        return private_key.decrypt(
            ciphertext,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                         algorithm=hashes.SHA256(), label=None)
        )
    elif encrypted_data[:1] == b'1':
        enc_aes_key = encrypted_data[1:257]
        enc_aes_iv = encrypted_data[257:513]
        enc_data = encrypted_data[513:]
        aes_key = private_key.decrypt(
            enc_aes_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                         algorithm=hashes.SHA256(), label=None)
        )
        aes_iv = private_key.decrypt(
            enc_aes_iv,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                         algorithm=hashes.SHA256(), label=None)
        )
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(aes_iv))
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(enc_data) + decryptor.finalize()
        return decrypted_data
    else:
        raise ValueError("Unsupported encrypted data format")
