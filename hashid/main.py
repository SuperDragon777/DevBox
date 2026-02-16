#!/usr/bin/env python3

import re
import argparse
import base64

HEX_HASH_TYPES = {
    32: [("MD5", 0.9), ("NTLM", 0.6)],
    40: [("SHA1", 0.9)],
    56: [("SHA224", 0.9)],
    64: [("SHA256", 0.9), ("SHA3-256", 0.6), ("BLAKE2s", 0.5)],
    96: [("SHA384", 0.9)],
    128: [("SHA512", 0.9), ("SHA3-512", 0.6), ("BLAKE2b", 0.5)],
}

def is_hex(s):
    return re.fullmatch(r"[0-9a-fA-F]+", s) is not None

def is_base64(s):
    try:
        base64.b64decode(s, validate=True)
        return True
    except Exception:
        return False

def identify_special(hash_string):
    if hash_string.startswith("$2a$") or hash_string.startswith("$2b$") or hash_string.startswith("$2y$"):
        return [("bcrypt", 0.99, "Адаптивный хеш паролей")]
    if hash_string.startswith("$argon2"):
        return [("Argon2", 0.99, "Современный алгоритм хеширования паролей")]
    if hash_string.startswith("$pbkdf2"):
        return [("PBKDF2", 0.95, "Производный ключ с итерациями")]
    if hash_string.startswith("$scrypt"):
        return [("scrypt", 0.95, "Память-зависимый алгоритм")]
    return None

def identify_hash(hash_string):
    hash_string = hash_string.strip()

    special = identify_special(hash_string)
    if special:
        return special

    if is_hex(hash_string):
        length = len(hash_string)
        if length in HEX_HASH_TYPES:
            return [(name, prob, "Hex-хеш") for name, prob in HEX_HASH_TYPES[length]]
        return [("Unknown hex", 0.2, "Неизвестный hex-формат")]

    if is_base64(hash_string):
        return [("Base64 encoded hash", 0.6, "Данные в Base64")]

    return [("Unknown", 0.0, "Не удалось определить")]


def main():
    parser = argparse.ArgumentParser(description="Hash identifier")
    parser.add_argument("hash", help="Строка хеша")
    args = parser.parse_args()

    results = identify_hash(args.hash)

    print("\nРезультаты:")
    for name, prob, desc in results:
        print(f"- {name} (вероятность: {prob*100:.0f}%) — {desc}")

if __name__ == "__main__":
    main()
