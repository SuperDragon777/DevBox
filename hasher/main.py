import hashlib
import sys

# remake of hasher from my old repo https://github.com/SuperDragon777/hash_bf

def hash_input(text: str, algorithms: list[str] | None = None) -> dict[str, str]:
    if not text:
        raise ValueError("Empty input!")
    
    text_bytes = text.encode('utf-8')
    
    available_hashes = {
        'MD5': lambda: hashlib.md5(text_bytes).hexdigest(),
        'SHA-1': lambda: hashlib.sha1(text_bytes).hexdigest(),
        'SHA-256': lambda: hashlib.sha256(text_bytes).hexdigest(),
        'SHA-512': lambda: hashlib.sha512(text_bytes).hexdigest(),
        'SHA3-256': lambda: hashlib.sha3_256(text_bytes).hexdigest(),
        'SHA3-512': lambda: hashlib.sha3_512(text_bytes).hexdigest(),
        'BLAKE2b': lambda: hashlib.blake2b(text_bytes).hexdigest(),
        'BLAKE2s': lambda: hashlib.blake2s(text_bytes).hexdigest(),
    }
    
    if algorithms:
        selected = {k: v for k, v in available_hashes.items() if k in algorithms}
    else:
        selected = available_hashes
    
    return {algo: hash_func() for algo, hash_func in selected.items()}


def display_hashes(text: str, hashes: dict[str, str]) -> None:
    print(f'\n{"="*70}')
    print(f'Hashing "{text}"')
    print(f'{"="*70}\n')
    
    max_algo_len = max(len(algo) for algo in hashes.keys())
    
    for algorithm, hash_value in hashes.items():
        print(f'{algorithm:<{max_algo_len}} : {hash_value}')
    
    print(f'\n{"="*70}\n')


def main():
    print('╔════════════════════════════════╗')
    print('║             HASHER             ║')
    print('╚════════════════════════════════╝\n')
    
    try:
        user_input = input('Enter text to hash: ').strip()
        
        if not user_input:
            print('Empty input!')
            sys.exit(1)
        
        result = hash_input(user_input)
        display_hashes(user_input, result)
        
    except KeyboardInterrupt:
        print('\n\nInterrupted by user.')
        sys.exit(0)
    except Exception as e:
        print(f'\nError: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()