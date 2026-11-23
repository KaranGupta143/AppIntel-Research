"""Optional, credential-gated example of the current Composio Python SDK."""
from __future__ import annotations

import importlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ComposioCheck:
    package_installed: bool
    api_key_configured: bool
    session_created: bool = False
    mcp_endpoint_created: bool = False
    detail: str = ""


def check_composio(api_key: str, create_mcp: bool = False) -> ComposioCheck:
    """Use real SDK calls only when the optional package and key are available."""
    try:
        importlib.import_module("composio")
        package_installed = True
    except ImportError:
        package_installed = False

    if not package_installed:
        return ComposioCheck(False, bool(api_key), detail="Composio package is not installed.")
    if not api_key:
        return ComposioCheck(True, False, detail="COMPOSIO_API_KEY is not configured.")

    try:
        from composio import Composio

        composio = Composio(api_key=api_key)
        session = composio.create(
            user_id="integration-research-readiness-check",
            mcp=create_mcp,
        )
        mcp_created = bool(
            create_mcp
            and getattr(session, "mcp", None)
            and getattr(session.mcp, "url", "")
        )
        return ComposioCheck(
            True,
            True,
            session_created=True,
            mcp_endpoint_created=mcp_created,
            detail=(
                "Session created successfully."
                if not create_mcp
                else "Hosted MCP endpoint created successfully."
                if mcp_created
                else "Session created, but no MCP endpoint URL was returned."
            ),
        )
    except Exception as exc:
        type_name = type(exc).__name__
        message = str(exc).strip().replace(api_key, "[REDACTED]")
        return ComposioCheck(
            True,
            True,
            detail=f"Composio SDK call failed ({type_name}): {message}",
        )
