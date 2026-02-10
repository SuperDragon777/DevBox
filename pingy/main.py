import argparse
import platform
import re
import subprocess
import sys
from typing import Iterable, List, Tuple
import urllib.error
import urllib.parse
import urllib.request


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


def ping_host(host: str, timeout_ms: int = 2000) -> Tuple[bool, float, str, int]:
    cmd = _build_ping_command(host, timeout_ms)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=False,
        )
    except FileNotFoundError:
        return False, 0.0, "ping command not found", -1
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
        return False, latency, "no response", proc.returncode
    if not ok:
        return False, latency, "unreachable", proc.returncode
    return True, latency, "", proc.returncode


def _build_http_url(host: str) -> str:
    parsed = urllib.parse.urlparse(host)
    if not parsed.scheme:
        return f"http://{host}"
    return host


def get_http_status(host: str, timeout_ms: int) -> Tuple[bool, int, str]:
    url = _build_http_url(host)
    timeout_s = max(1.0, timeout_ms / 1000.0)
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:
            status = getattr(resp, "status", 0)
            ok = 200 <= status < 400
            return ok, int(status), ""
    except urllib.error.HTTPError as e:
        status = getattr(e, "code", 0)
        return False, int(status), e.reason or "HTTP error"
    except Exception as e:
        return False, 0, str(e)


def _format_single_result(
    host: str,
    ok: bool,
    latency: float,
    message: str,
    ping_code: int,
    http_status: int | None,
) -> str:
    status_color = GREEN if ok else RED
    status_text = "UP" if ok else "DOWN"
    latency_text = f"{latency:.1f} ms" if latency > 0 else "-"
    host_field = f"{host:<30}"
    status_field = f"{status_text:^10}"
    parts = []
    if ok:
        parts.append(f"latency {latency_text}")
    else:
        parts.append(message or "no reply")

    parts.append(f"ping_rc {ping_code}")

    if http_status is not None and http_status != 0:
        parts.append(f"http {http_status}")

    detail_plain = ", ".join(parts)
    line_plain = f" {host_field} {status_field} {detail_plain}"
    host_colored = f"{CYAN}{host_field}{RESET}"
    status_colored = f"{status_color}{status_field}{RESET}"
    detail_colored = f"{DIM}{detail_plain}{RESET}"
    line_colored = f" {host_colored} {status_colored} {detail_colored}"
    border = "─" * (len(line_plain) + 1)
    return f"┌{border}┐\n│{line_colored} │\n└{border}┘"


def ping_hosts(
    hosts: Iterable[str],
    timeout_ms: int = 2000,
    output_path: str | None = None,
    check_http: bool = False,
) -> None:
    cleaned_hosts = [h.strip() for h in hosts if h and h.strip()]
    if not cleaned_hosts:
        print(f"{YELLOW}No hosts provided{RESET}")
        return

    print(f"{CYAN}Pingy host availability check{RESET}")
    print(f"{DIM}{'=' * 40}{RESET}")

    up_count = 0
    down_count = 0
    file_lines: List[str] = []

    if output_path:
        file_lines.append("Pingy host availability check")
        file_lines.append("=" * 40)

    for host in cleaned_hosts:
        ok, latency, msg, ping_code = ping_host(host, timeout_ms=timeout_ms)

        http_status: int | None = None
        http_ok = False
        http_msg = ""
        if check_http:
            http_ok, http_status, http_msg = get_http_status(host, timeout_ms)
            if not ok and http_ok:
                ok = True
                msg = http_msg

        formatted = _format_single_result(
            host,
            ok,
            latency,
            msg,
            ping_code,
            http_status,
        )
        print(formatted)

        if ok:
            up_count += 1
        else:
            down_count += 1

        if output_path:
            status_text = "UP" if ok else "DOWN"
            latency_text = f"{latency:.1f} ms" if latency > 0 else "-"

            parts = []
            if ok:
                parts.append(f"latency {latency_text}")
            else:
                parts.append(msg or "no reply")
            parts.append(f"ping_rc {ping_code}")
            if http_status is not None and http_status != 0:
                parts.append(f"http {http_status}")

            detail_plain = ", ".join(parts)
            file_lines.append(
                f"{host};{status_text};{latency_text};{detail_plain}"
            )

    total = len(cleaned_hosts)
    print(f"{DIM}{'-' * 40}{RESET}")
    print(
        f"{GREEN}UP: {up_count}{RESET}, "
        f"{RED}DOWN: {down_count}{RESET}, "
        f"{CYAN}TOTAL: {total}{RESET}"
    )

    if output_path:
        file_lines.append("")
        file_lines.append(f"UP: {up_count}, DOWN: {down_count}, TOTAL: {total}")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(file_lines) + "\n")
        except OSError:
            print(f"{RED}Cannot write results file: {output_path}{RESET}", file=sys.stderr)


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
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        help="Path to save results to a file",
    )
    parser.add_argument(
        "--http",
        dest="http",
        action="store_true",
        help="Also perform HTTP request and show HTTP status code (200, 404, etc.)",
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
    ping_hosts(
        hosts,
        timeout_ms=args.timeout,
        output_path=args.output,
        check_http=args.http,
    )


if __name__ == "__main__":
    main()

