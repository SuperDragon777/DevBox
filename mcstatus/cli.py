import argparse
import json
from server_info import get_server_info


def main():
    parser = argparse.ArgumentParser(description="Minecraft server info utility")
    parser.add_argument("host", help="Адрес сервера")
    parser.add_argument(
        "--type",
        choices=["java", "bedrock"],
        default="java",
        help="Тип сервера (java / bedrock)",
    )
    parser.add_argument("--port", type=int, help="Порт сервера")
    parser.add_argument("--json", action="store_true", help="Вывод в JSON")

    args = parser.parse_args()

    info = get_server_info(
        host=args.host,
        port=args.port,
        server_type=args.type,
    )

    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return

    if not info["online"]:
        print("❌ Сервер недоступен")
        print(f"Причина: {info.get('error')}")
        return

    print(f"🎮 Сервер: {info['host']}:{info['port']}")
    print(f"🧩 Тип: {info['type']}")
    print(f"⏱ Пинг: {info['latency_ms']} ms")
    print(f"👥 Игроки: {info['players']['online']} / {info['players']['max']}")
    print(f"📝 MOTD: {info['motd']}")

    if info["type"] == "java" and info["players"].get("sample"):
        print("👤 Онлайн игроки:")
        for p in info["players"]["sample"]:
            print(f" - {p}")


if __name__ == "__main__":
    main()
