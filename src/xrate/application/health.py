# src/xrate/application/health.py
"""
Health Checker - System Monitoring and Diagnostics

This module provides comprehensive health monitoring for all bot components.
It checks the status of crawlers (Bonbast, AlanChand), APIs (Navasan, Wallex), Avalai wallet,
state manager, and data fetching operations to ensure the bot is operating correctly and identify issues.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from xrate.application.state_manager import state_manager
from xrate.adapters.providers.navasan import NavasanProvider
from xrate.adapters.providers.wallex import WallexProvider
from xrate.adapters.ai.avalai import AvalaiService
from xrate.application.rates_service import get_irr_snapshot
from xrate.application.crawler_service import get_crawler_usage_times  # Get crawler usage times
from xrate.config import settings
import requests  # type: ignore[import-untyped]  # HTTP library for Avalai wallet check

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Represents the health status of a component."""
    is_healthy: bool
    message: str
    last_check: datetime
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """Centralized health checking for all bot components."""
    
    def __init__(self):
        self.navasan_provider = NavasanProvider()
        self.wallex_provider = WallexProvider()
        self.avalai_service = AvalaiService()
    
    def check_crawlers(self) -> HealthStatus:
        """Check crawler health status."""
        try:
            from xrate.application.crawler_service import get_crawler_snapshot
            crawler1_time, crawler2_time = get_crawler_usage_times()
            
            # Try to get a snapshot
            snap = get_crawler_snapshot()
            
            crawler1_status = "Last used: " + (crawler1_time.strftime("%Y-%m-%d %H:%M:%S UTC") if crawler1_time else "Never")
            crawler2_status = "Last used: " + (crawler2_time.strftime("%Y-%m-%d %H:%M:%S UTC") if crawler2_time else "Never")
            
            if snap:
                return HealthStatus(
                    is_healthy=True,
                    message=f"Crawlers healthy. Provider: {snap.provider}. Crawler1: {crawler1_status}, Crawler2: {crawler2_status}",
                    last_check=datetime.now(timezone.utc),
                    details={
                        "provider": snap.provider,
                        "crawler1_last_used": crawler1_time.isoformat() if crawler1_time else None,
                        "crawler2_last_used": crawler2_time.isoformat() if crawler2_time else None,
                        "usd": snap.usd_toman,
                        "eur": snap.eur_toman,
                        "gold": snap.gold_1g_toman,
                    }
                )
            else:
                return HealthStatus(
                    is_healthy=False,
                    message=f"Crawlers unavailable. Crawler1: {crawler1_status}, Crawler2: {crawler2_status}",
                    last_check=datetime.now(timezone.utc),
                    details={
                        "crawler1_last_used": crawler1_time.isoformat() if crawler1_time else None,
                        "crawler2_last_used": crawler2_time.isoformat() if crawler2_time else None,
                    }
                )
        except Exception as e:
            logger.error("Crawler health check failed: %s", e)
            return HealthStatus(
                is_healthy=False,
                message=f"Crawler error: {str(e)}",
                last_check=datetime.now(timezone.utc)
            )
    
    def check_avalai_wallet(self) -> HealthStatus:
        """
        Check Avalai wallet credit.
        
        Uses the Avalai API to get remaining credit in Iranian Toman (remaining_irt).
        """
        try:
            if not settings.avalai_key:
                return HealthStatus(
                    is_healthy=False,
                    message="Avalai API key not configured",
                    last_check=datetime.now(timezone.utc),
                    details={"configured": False}
                )
            
            url = "https://api.avalai.ir/user/credit"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.avalai_key}"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract remaining_irt (remaining credit in Iranian Toman)
            if isinstance(data, dict):
                remaining_irt = data.get("remaining_irt", 0)
                # Format as integer (remove decimals if any)
                credit_toman = int(float(remaining_irt))
                
                # Format credit nicely for display
                if credit_toman >= 1_000_000:
                    credit_display = f"{credit_toman / 1_000_000:.2f}M تومان"
                elif credit_toman >= 1_000:
                    credit_display = f"{credit_toman / 1_000:.2f}K تومان"
                else:
                    credit_display = f"{credit_toman} تومان"
                
                return HealthStatus(
                    is_healthy=True,
                    message=f"Avalai wallet: {credit_display} ({credit_toman:,} تومان)",
                    last_check=datetime.now(timezone.utc),
                    details={
                        "remaining_irt": credit_toman,
                        "credit_display": credit_display,
                        "raw_response": data
                    }
                )
            else:
                return HealthStatus(
                    is_healthy=False,
                    message="Avalai API returned invalid response format",
                    last_check=datetime.now(timezone.utc),
                    details={"raw_response": data}
                )
        except Exception as e:
            logger.error("Avalai wallet check failed: %s", e)
            return HealthStatus(
                is_healthy=False,
                message=f"Avalai wallet error: {str(e)}",
                last_check=datetime.now(timezone.utc)
            )
    
    def check_navasan_api(self) -> HealthStatus:
        """Check Navasan API health."""
        try:
            vals = self.navasan_provider.get_values(["usd", "eur", "18ayar"])
            count = len([v for v in vals.values() if v])
            return HealthStatus(
                is_healthy=True,
                message=f"Navasan API healthy, {count} data points",
                last_check=datetime.now(timezone.utc),
                details={"data_points": count, "values": vals}
            )
        except Exception as e:
            logger.error("Navasan health check failed: %s", e)
            return HealthStatus(
                is_healthy=False,
                message=f"Navasan API error: {str(e)}",
                last_check=datetime.now(timezone.utc)
            )
    
    def check_wallex_api(self) -> HealthStatus:
        """Check Wallex API health (Tether/USDT-TMN data)."""
        try:
            tether_data = self.wallex_provider.get_tether_data()
            if tether_data and "price" in tether_data and "24h_ch" in tether_data:
                price = tether_data["price"]
                ch_24h = tether_data["24h_ch"]
                return HealthStatus(
                    is_healthy=True,
                    message=f"Wallex API healthy, USDT price: {int(price)}, 24h_ch: {ch_24h:.2f}%",
                    last_check=datetime.now(timezone.utc),
                    details={
                        "price": price,
                        "24h_ch": ch_24h,
                        "price_toman": int(price)
                    }
                )
            else:
                return HealthStatus(
                    is_healthy=False,
                    message="Wallex API returned incomplete Tether data",
                    last_check=datetime.now(timezone.utc),
                    details={"tether_data": tether_data}
                )
        except Exception as e:
            logger.error("Wallex health check failed: %s", e)
            return HealthStatus(
                is_healthy=False,
                message=f"Wallex API error: {str(e)}",
                last_check=datetime.now(timezone.utc)
            )
    
    def check_state_manager(self) -> HealthStatus:
        """Check state manager health."""
        try:
            current_state = state_manager.get_current_state()
            if current_state:
                elapsed = state_manager.get_elapsed_seconds()
                return HealthStatus(
                    is_healthy=True,
                    message=f"State manager healthy, last update: {elapsed}s ago",
                    last_check=datetime.now(timezone.utc),
                    details={
                        "has_state": True,
                        "elapsed_seconds": elapsed,
                        "timestamp": current_state.ts.isoformat() if current_state.ts else None
                    }
                )
            else:
                return HealthStatus(
                    is_healthy=True,
                    message="State manager healthy, no state yet (first run)",
                    last_check=datetime.now(timezone.utc),
                    details={"has_state": False}
                )
        except Exception as e:
            logger.error("State manager health check failed: %s", e)
            return HealthStatus(
                is_healthy=False,
                message=f"State manager error: {str(e)}",
                last_check=datetime.now(timezone.utc)
            )
    
    def check_irr_data_fetch(self) -> HealthStatus:
        """Check IRR data fetching health."""
        try:
            snap = get_irr_snapshot()
            if snap:
                return HealthStatus(
                    is_healthy=True,
                    message="IRR data fetch successful",
                    last_check=datetime.now(timezone.utc),
                    details={
                        "usd": snap.usd_toman,
                        "eur": snap.eur_toman,
                        "gold": snap.gold_1g_toman,
                        "provider": snap.provider
                    }
                )
            else:
                return HealthStatus(
                    is_healthy=False,
                    message="IRR data fetch failed (all providers unavailable)",
                    last_check=datetime.now(timezone.utc)
                )
        except Exception as e:
            logger.error("IRR data fetch health check failed: %s", e)
            return HealthStatus(
                is_healthy=False,
                message=f"IRR data fetch error: {str(e)}",
                last_check=datetime.now(timezone.utc)
            )
    
    def check_avalai_api(self) -> HealthStatus:
        """Check Avalai API health by sending a test message."""
        try:
            if not self.avalai_service.client:
                return HealthStatus(
                    is_healthy=False,
                    message="Avalai API not configured (API key missing)",
                    last_check=datetime.now(timezone.utc),
                    details={"configured": False}
                )
            
            logger.info("Checking Avalai API health with test message")
            success, response = self.avalai_service.test_api()
            
            if success:
                logger.info("Avalai API health check passed. Response: %s", response)
                return HealthStatus(
                    is_healthy=True,
                    message=f"Avalai API healthy, response: {response[:80]}..." if len(response) > 80 else f"Avalai API healthy, response: {response}",
                    last_check=datetime.now(timezone.utc),
                    details={
                        "response": response,
                        "response_length": len(response),
                        "test_message": "در یک کلمه بگو آیا همه چیز اوکیه؟"
                    }
                )
            else:
                logger.warning("Avalai API health check failed: %s", response)
                return HealthStatus(
                    is_healthy=False,
                    message=f"Avalai API unhealthy: {response}",
                    last_check=datetime.now(timezone.utc),
                    details={"error": response}
                )
        except Exception as e:
            logger.error("Avalai API health check failed with exception: %s", e, exc_info=True)
            return HealthStatus(
                is_healthy=False,
                message=f"Avalai API error: {str(e)}",
                last_check=datetime.now(timezone.utc),
                details={"exception": str(e), "exception_type": type(e).__name__}
            )
    
    def get_overall_health(self) -> Dict[str, Any]:
        """
        Get overall health status of all components.
        
        Returns degraded status if any critical component fails, even if others are healthy.
        """
        checks = {
            "crawlers": self.check_crawlers(),
            "navasan": self.check_navasan_api(),
            "wallex": self.check_wallex_api(),
            "avalai": self.check_avalai_api(),
            "avalai_wallet": self.check_avalai_wallet(),
            "state_manager": self.check_state_manager(),
            "irr_data": self.check_irr_data_fetch(),
        }
        
        # Aggregate status: degraded if any critical component fails
        healthy_checks = [name for name, check in checks.items() if check.is_healthy]
        failed_checks = [name for name, check in checks.items() if not check.is_healthy]
        
        # Overall healthy only if ALL checks pass
        overall_healthy = len(failed_checks) == 0
        
        # Generate status message
        if overall_healthy:
            status_message = "All systems healthy"
        else:
            failed_messages = [f"{name}: {checks[name].message}" for name in failed_checks]
            status_message = f"Degraded - {len(failed_checks)} component(s) failed: {', '.join(failed_checks)}"
        
        return {
            "overall_healthy": overall_healthy,
            "status": "healthy" if overall_healthy else "degraded",
            "message": status_message,
            "healthy_components": healthy_checks,
            "failed_components": failed_checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                name: {
                    "healthy": check.is_healthy,
                    "message": check.message,
                    "last_check": check.last_check.isoformat(),
                    "details": check.details
                }
                for name, check in checks.items()
            }
        }


# Global health checker instance
health_checker = HealthChecker()
