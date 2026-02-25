"""
Logging Service Module

This module provides centralized logging services for the Ginkgo trading system.
It includes:
- Log service for unified logging interface
- Client implementations for various logging backends (Loki, etc.)

Example:
    from ginkgo.services.logging import LogService, LokiClient
"""

from ginkgo.services.logging.log_service import LogService

__all__ = ["LogService"]
