import sys


SUPPORTED_BASES = (2, 8, 10, 16)


def parse_base(value: str) -> int:
    try:
        base = int(value)
    except ValueError:
        raise ValueError("Base must be an integer.")

    if base not in SUPPORTED_BASES:
        raise ValueError(
            f"Only these bases are supported: {', '.join(map(str, SUPPORTED_BASES))}."
        )
    return base


def convert_number(num_str: str, from_base: int, to_base: int) -> str:
    try:
        value = int(num_str, from_base)
    except ValueError:
        raise ValueError(
            f"'{num_str}' is not a valid number in base {from_base}."
        )

    if to_base == 10:
        return str(value)
    if to_base == 2:
        return bin(value)[2:] if value >= 0 else "-" + bin(-value)[2:]
    if to_base == 8:
        return oct(value)[2:] if value >= 0 else "-" + oct(-value)[2:]
    if to_base == 16:
        return hex(value)[2:].upper() if value >= 0 else "-" + hex(-value)[2:].upper()

    raise ValueError(f"Unsupported target base: {to_base}")


def interactive_mode() -> None:
    print("=== Base Converter (2 / 8 / 10 / 16) ===")
    print("Type 'q' in any field to exit.\n")

    while True:
        try:
            src_base_str = input("Source base (2/8/10/16): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        if src_base_str.lower() == "q":
            print("Exiting.")
            return

        try:
            src_base = parse_base(src_base_str)
        except ValueError as e:
            print(f"Error: {e}\n")
            continue

        dst_base_str = input("Target base (2/8/10/16): ").strip()
        if dst_base_str.lower() == "q":
            print("Exiting.")
            return

        try:
            dst_base = parse_base(dst_base_str)
        except ValueError as e:
            print(f"Error: {e}\n")
            continue

        num_str = input(f"Number in base {src_base}: ").strip()
        if num_str.lower() == "q":
            print("Exiting.")
            return

        try:
            result = convert_number(num_str, src_base, dst_base)
        except ValueError as e:
            print(f"Error: {e}\n")
            continue

        print(f"Result ({src_base} → {dst_base}): {result}\n")


def cli(args: list[str]) -> None:
    if len(args) == 0:
        interactive_mode()
        return

    if len(args) != 3:
        print("Usage: python main.py <number> <from_base> <to_base>")
        print("Or run without arguments for interactive mode.")
        sys.exit(1)

    num_str, from_str, to_str = args

    try:
        from_base = parse_base(from_str)
        to_base = parse_base(to_str)
        result = convert_number(num_str, from_base, to_base)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    cli(sys.argv[1:])