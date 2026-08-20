"""Fail CI if hosted ContextDB implementation enters the public client repo."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (
    ROOT / "python" / "contextdb_cloud_client",
    ROOT / "typescript" / "src",
    ROOT / "starters",
)
FORBIDDEN = {
    "ConnectorWorker",
    "ConnectorStore",
    "EntitlementResolver",
    "GatewayMemorySink",
    "GcpSecretManagerResolver",
    "PlaneStore",
    "contextdb_cloud.gateway",
    "contextdb_cloud.console_api",
}


def check() -> list[str]:
    errors: list[str] = []
    constitution = ROOT / "PUBLIC_BOUNDARY.md"
    if not constitution.is_file():
        errors.append("PUBLIC_BOUNDARY.md is required")
    for source_root in SOURCE_ROOTS:
        if not source_root.exists():
            errors.append(f"missing public source root: {source_root.relative_to(ROOT)}")
            continue
        for path in source_root.rglob("*"):
            if (
                not path.is_file()
                or any(part in {"node_modules", ".venv"} for part in path.parts)
                or path.suffix not in {".py", ".ts", ".tsx", ".js", ".mjs"}
            ):
                continue
            text = path.read_text(errors="replace")
            for token in FORBIDDEN:
                if token in text:
                    errors.append(
                        f"{path.relative_to(ROOT)} contains private symbol {token}"
                    )
    return errors


if __name__ == "__main__":
    failures = check()
    if failures:
        for failure in failures:
            print(f"boundary: {failure}")
        raise SystemExit(1)
    print("public client boundary passed")
