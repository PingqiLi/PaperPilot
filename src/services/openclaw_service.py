
"""
OpenClaw Service - OpenClaw Client Singleton
"""
from ..config import settings
from .openclaw_client import OpenClawClient

# Global OpenClaw Client Instance
openclaw_client = OpenClawClient(
    uri=settings.openclaw_gateway_uri,
    token=settings.openclaw_gateway_token
)
