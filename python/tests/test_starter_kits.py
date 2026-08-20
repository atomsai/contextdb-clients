from __future__ import annotations

import ast
import importlib.metadata
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STARTERS = ROOT / "starters"
EXPECTED = {
    "openai-agents-python",
    "langgraph-python",
    "livekit-agents-python",
    "vercel-ai-sdk",
    "pyai-omni",
}


def test_all_documented_starter_directories_exist() -> None:
    hub = (STARTERS / "README.md").read_text()
    for name in EXPECTED:
        directory = STARTERS / name
        assert directory.is_dir()
        assert (directory / "README.md").is_file()
        assert f"({name}/)" in hub


def test_python_starters_parse_and_pin_public_client() -> None:
    for name in (
        "openai-agents-python",
        "langgraph-python",
        "livekit-agents-python",
    ):
        source = (STARTERS / name / "agent.py").read_text()
        ast.parse(source)
        requirements = (STARTERS / name / "requirements.txt").read_text()
        assert "contextdb-cloud-client==0.1.0a3" in requirements
        assert "CONTEXTDB_API_KEY" in source


def test_typescript_starters_are_server_only_and_install_cloud_client() -> None:
    for name in ("vercel-ai-sdk", "pyai-omni"):
        directory = STARTERS / name
        package = json.loads((directory / "package.json").read_text())
        assert package["private"] is True
        assert "@contextdb/cloud" in package["dependencies"]
        source_name = "index.ts" if name == "vercel-ai-sdk" else "server.ts"
        source = (directory / source_name).read_text()
        assert "process.env" in source
        assert "CONTEXTDB_API_KEY" in source
        assert "https://api.contextdb.ai" in source


def test_every_starter_warns_that_keys_are_server_credentials() -> None:
    for name in EXPECTED:
        readme = (STARTERS / name / "README.md").read_text().lower()
        assert "server" in readme
        assert "contextdb_api_key" in readme
        assert "memory testbench" in readme


def test_python_exported_version_matches_package_metadata() -> None:
    from contextdb_cloud_client import __version__

    assert __version__ == importlib.metadata.version(
        "contextdb-cloud-client"
    )
