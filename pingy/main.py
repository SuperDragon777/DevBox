import argparse
import platform
import re
import subprocess
import sys
from typing import Iterable, List, Tuple


RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
DIM = "\033[2m"


def _build_ping_command(host: str, timeout_ms: int) -> List[str]:
    system = platform.system().lower()
    if system == "windows":
        return ["ping", "-n", "1", "-w", str(timeout_ms), host]
    timeout_s = max(1, int(round(timeout_ms / 1000)))
    return ["ping", "-c", "1", "-W", str(timeout_s), host]


def _extract_latency(output: str) -> Tuple[bool, float]:
    patterns = [
        r"Среднее\s*=\s*([\d\.]+)\s*мсек",
        r"Average\s*=\s*([\d\.]+)\s*ms",
        r"avg[/=]\s*([\d\.]+)\s*ms",
        r"time[=<]([\d\.]+)\s*ms",
        r"время[=<]([\d\.]+)\s*мс",
        r"([\d\.]+)\s*(?:ms|msec|мс|мсек)",
    ]
    for p in patterns:
        m = re.search(p, output, re.IGNORECASE)
        if not m:
            continue
        try:
            return True, float(m.group(1))
        except ValueError:
            continue
    return False, 0.0


def ping_host(host: str, timeout_ms: int = 2000) -> Tuple[bool, float, str]:
    cmd = _build_ping_command(host, timeout_ms)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=False,
        )
    except FileNotFoundError:
        return False, 0.0, "ping command not found"
    raw_out = proc.stdout or b""
    raw_err = proc.stderr or b""
    decoded_out = ""
    decoded_err = ""
    for enc in ("cp866", "cp1251", "utf-8"):
        if not decoded_out:
            try:
                decoded_out = raw_out.decode(enc, errors="ignore")
            except Exception:
                decoded_out = ""
        if not decoded_err:
            try:
                decoded_err = raw_err.decode(enc, errors="ignore")
            except Exception:
                decoded_err = ""
    output = decoded_out + decoded_err
    ok = proc.returncode == 0
    has_latency, latency = _extract_latency(output)
    if not has_latency:
        latency = 0.0
    if not ok and not output.strip():
        return False, latency, "no response"
    if not ok:
        return False, latency, "unreachable"
    return True, latency, ""


def _format_single_result(host: str, ok: bool, latency: float, message: str) -> str:
    status_color = GREEN if ok else RED
    status_text = "UP" if ok else "DOWN"
    latency_text = f"{latency:.1f} ms" if latency > 0 else "-"
    host_field = f"{host:<30}"
    status_field = f"{status_text:^10}"
    if ok:
        detail_plain = f"latency {latency_text}"
    else:
        detail_plain = message or "no reply"
    line_plain = f" {host_field} {status_field} {detail_plain}"
    host_colored = f"{CYAN}{host_field}{RESET}"
    status_colored = f"{status_color}{status_field}{RESET}"
    detail_colored = f"{DIM}{detail_plain}{RESET}"
    line_colored = f" {host_colored} {status_colored} {detail_colored}"
    border = "─" * (len(line_plain) + 1)
    return f"┌{border}┐\n│{line_colored} │\n└{border}┘"


def ping_hosts(hosts: Iterable[str], timeout_ms: int = 2000) -> None:
    cleaned_hosts = [h.strip() for h in hosts if h and h.strip()]
    if not cleaned_hosts:
        print(f"{YELLOW}No hosts provided{RESET}")
        return
    print(f"{CYAN}Pingy host availability check{RESET}")
    print(f"{DIM}{'=' * 40}{RESET}")
    for host in cleaned_hosts:
        ok, latency, msg = ping_host(host, timeout_ms=timeout_ms)
        formatted = _format_single_result(host, ok, latency, msg)
        print(formatted)


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pingy", add_help=True)
    parser.add_argument("hosts", nargs="*", help="Hosts to ping")
    parser.add_argument(
        "-f",
        "--file",
        dest="file",
        help="Path to file with hosts (one per line)",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        dest="timeout",
        type=int,
        default=2000,
        help="Timeout per host in ms",
    )
    return parser.parse_args(argv)


def _load_hosts_from_file(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except OSError:
        print(f"{RED}Cannot read hosts file: {path}{RESET}", file=sys.stderr)
        return []


def main(argv: List[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    args = _parse_args(argv)
    hosts: List[str] = []
    if args.file:
        hosts.extend(_load_hosts_from_file(args.file))
    if args.hosts:
        hosts.extend(args.hosts)
    if not hosts:
        print(f"{YELLOW}Provide at least one host or a file with hosts{RESET}")
        sys.exit(1)
    ping_hosts(hosts, timeout_ms=args.timeout)


if __name__ == "__main__":
    main()

