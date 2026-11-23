"""Shared extraction and output schemas for the research pipeline."""
from __future__ import annotations

AUTH_METHODS = ("OAuth2", "API key", "Bearer token", "Basic", "JWT", "Other", "Unknown")
ACCESS_TYPES = ("Self-serve", "Paid plan required", "Approval required",
                "Contact sales / partner", "Unknown")
API_TYPES = ("REST", "GraphQL", "SOAP", "gRPC", "SDK/CLI only", "Other", "Unknown")
MCP_TYPES = ("Official", "Community", "None found", "Unknown")
BUILDABILITY_TYPES = ("Easy", "Medium", "Difficult", "Not Feasible", "Unknown")
BLOCKER_TYPES = ("None", "Partner / approval gate", "Paid plan", "No public API",
                 "Complex auth", "Rate limits / quotas", "Other", "Unknown")

EXTRACTION_SCHEMA = """{
 "description": "one line on what the app does",
 "auth_methods": ["OAuth2|API key|Bearer token|Basic|JWT|Other|Unknown"],
 "auth_sources": ["official evidence URLs that support authentication, or []"],
 "access": "Self-serve|Paid plan required|Approval required|Contact sales / partner|Unknown",
 "api_types": ["REST|GraphQL|SOAP|gRPC|SDK/CLI only|Other|Unknown"],
 "api_breadth": "main resources, max 20 words",
 "api_sources": ["official evidence URLs that support API availability, or []"],
 "mcp": "Official|Community|None found|Unknown",
 "mcp_sources": ["evidence URLs that support MCP availability, or []"],
 "mcp_url": "official MCP URL from the evidence pages or empty string",
 "buildability": "Easy|Medium|Difficult|Not Feasible|Unknown",
 "blocker_type": "None|Partner / approval gate|Paid plan|No public API|Complex auth|Rate limits / quotas|Other|Unknown",
 "blocker": "main blocker in one sentence, or 'Unknown'",
 "sources": ["only URLs from the evidence pages that support at least one answer"],
 "notes": "uncertainty or conflicts"
}"""
