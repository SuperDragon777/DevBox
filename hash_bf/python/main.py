import hashlib
import itertools
import string

# remake of hash_bf from my old repo https://github.com/SuperDragon777/hash_bf
# please do not use it for bad purposes!

def get_hash_function():
    print("\nAvailable hash functions:")
    print("1) MD5")
    print("2) SHA-1")
    print("3) SHA-256")
    print("4) SHA-512")
    
    choice = input("Choose a hash function (1-4): ").strip()
    
    hash_functions = {
        '1': hashlib.md5,
        '2': hashlib.sha1,
        '3': hashlib.sha256,
        '4': hashlib.sha512
    }
    
    return hash_functions.get(choice, hashlib.md5)

def crack_hash(target_hash, hash_func, charset=string.printable.strip(), max_length=6):
    total_attempts = 0
    func_name = hash_func().__class__.__name__.replace('_', '').upper()
    
    print(f"\n[+] Using hash function: {func_name}")
    print(f"[+] Charset: {len(charset)} symbols")
    print(f"[+] Maximum length: {max_length}\n")
    
    for length in range(1, max_length + 1):
        for attempt in itertools.product(charset, repeat=length):
            candidate = ''.join(attempt)
            candidate_hash = hash_func(candidate.encode()).hexdigest()
            total_attempts += 1
            
            if total_attempts % 1000 == 0:
                print(f"[{total_attempts}] {candidate} -> {candidate_hash}")
            
            if candidate_hash == target_hash:
                print(f"\n[+] Found password in {total_attempts}!")
                return candidate, total_attempts
    return None, total_attempts

if __name__ == "__main__":
    print("=== Hash Brute Force ===")
    
    hash_func = get_hash_function()
    
    target = input("\nEnter the hash: ").strip().lower()
    
    try:
        max_len = int(input("Maximum password length: ").strip())
        if max_len > 8:
            print("[!] Warning: It will take a very long time to iterate through more than 8 characters!")
    except ValueError:
        print("[!] Invalid input. Using default value (5).")
        max_len = 5
    
    print("\nSelect charset:")
    print("1) Only numerals (0-9)")
    print("2) Only lowercase letters (a-z)")
    print("3) All letters and numerals (a-z, A-Z, 0-9)")
    print("4) Any printable character")
    
    charset_choice = input("Your choice (1-4): ").strip()
    
    charsets = {
        '1': string.digits,
        '2': string.ascii_lowercase,
        '3': string.ascii_letters + string.digits,
        '4': string.printable.strip()
    }
    
    charset = charsets.get(charset_choice, string.digits)
    
    print("\n" + "="*50)
    result, attempts = crack_hash(target, hash_func, charset, max_len)
    
    print("\n" + "="*50)
    if result:
        print(f"[+] Done! Password: '{result}'")
    else:
        print(f"[-] Password not found.")
    print(f"[+] Total attempts: {attempts}")
    print("="*50)