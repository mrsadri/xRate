# src/xrate/application/health.py
"""
Health Checker - System Monitoring and Diagnostics

This module provides comprehensive health monitoring for all bot components.
It checks the status of APIs (BRS, FastForex, Navasan, Wallex), state manager, and data
fetching operations to ensure the bot is operating correctly and identify issues.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from xrate.application.state_manager import state_manager
from xrate.adapters.providers.brsapi import BRSAPIProvider
from xrate.adapters.providers.fastforex import FastForexProvider
from xrate.adapters.providers.navasan import NavasanProvider
from xrate.adapters.providers.wallex import WallexProvider
from xrate.adapters.ai.avalai import AvalaiService
from xrate.application.rates_service import get_irr_snapshot

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
        self.brsapi_provider = BRSAPIProvider()
        self.fastforex_provider = FastForexProvider()
        self.navasan_provider = NavasanProvider()
        self.wallex_provider = WallexProvider()
        self.avalai_service = AvalaiService()
    
    def check_brsapi_api(self) -> HealthStatus:
        """Check BRS API health."""
        try:
            usd = self.brsapi_provider.get_usd_toman()
            eur = self.brsapi_provider.get_eur_toman()
            gold = self.brsapi_provider.get_gold_18k_toman()
            eurusd = self.brsapi_provider.eur_usd_rate()
            
            if usd and eur and gold:
                return HealthStatus(
                    is_healthy=True,
                    message=f"BRS API healthy, USD={usd}, EUR={eur}, Gold={gold}, EUR/USD={eurusd:.4f}",
                    last_check=datetime.now(timezone.utc),
                    details={"usd": usd, "eur": eur, "gold": gold, "eurusd": eurusd}
                )
            else:
                return HealthStatus(
                    is_healthy=False,
                    message="BRS API returned incomplete data",
                    last_check=datetime.now(timezone.utc),
                    details={"usd": usd, "eur": eur, "gold": gold}
                )
        except Exception as e:
            logger.error("BRS API health check failed: %s", e)
            return HealthStatus(
                is_healthy=False,
                message=f"BRS API error: {str(e)}",
                last_check=datetime.now(timezone.utc)
            )
    
    def check_fastforex_api(self) -> HealthStatus:
        """Check FastForex API health."""
        try:
            rate = self.fastforex_provider.eur_usd_rate()
            return HealthStatus(
                is_healthy=True,
                message=f"FastForex API healthy, rate: {rate:.4f}",
                last_check=datetime.now(timezone.utc),
                details={"rate": rate}
            )
        except Exception as e:
            logger.error("FastForex health check failed: %s", e)
            return HealthStatus(
                is_healthy=False,
                message=f"FastForex API error: {str(e)}",
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
                        "test_message": "آیا همه چیز اوکیه؟"
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
            "brsapi": self.check_brsapi_api(),
            "fastforex": self.check_fastforex_api(),
            "navasan": self.check_navasan_api(),
            "wallex": self.check_wallex_api(),
            "avalai": self.check_avalai_api(),
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
