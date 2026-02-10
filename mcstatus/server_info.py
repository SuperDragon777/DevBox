from mcstatus import JavaServer, BedrockServer
from typing import Dict, Any, Literal


ServerType = Literal["java", "bedrock"]


def get_server_info(
    host: str,
    port: int | None = None,
    server_type: ServerType = "java",
    timeout: int = 5,
) -> Dict[str, Any]:
    try:
        if server_type == "java":
            server = JavaServer(host, port or 25565, timeout=timeout)
            status = server.status()
            latency = server.ping()

            return {
                "type": "java",
                "online": True,
                "host": host,
                "port": port or 25565,
                "latency_ms": round(latency, 2),
                "version": status.version.name,
                "players": {
                    "online": status.players.online,
                    "max": status.players.max,
                    "sample": [p.name for p in status.players.sample]
                    if status.players.sample else [],
                },
                "motd": status.description,
            }

        elif server_type == "bedrock":
            server = BedrockServer(host, port or 19132)
            status = server.status()

            return {
                "type": "bedrock",
                "online": True,
                "host": host,
                "port": port or 19132,
                "latency_ms": round(status.latency, 2),
                "version": status.version.name,
                "players": {
                    "online": status.players.online,
                    "max": status.players.max,
                },
                "motd": status.motd,
            }

        else:
            raise ValueError("Unknown server type")

    except Exception as e:
        return {
            "online": False,
            "host": host,
            "port": port,
            "type": server_type,
            "error": str(e),
        }
