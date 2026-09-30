"""
Risk & Event Processing Service.
Handles dynamic risk index computations, severity categorizations, and event ingestion.
"""

from typing import List, Optional, Dict, Any
from app.database.json_repository import JSONRepository, get_repository


class RiskService:
    def __init__(self, repo: Optional[JSONRepository] = None):
        self.repo = repo or get_repository()

    def get_driver_risk(self, driver_id: str) -> Optional[Dict[str, Any]]:
        return self.repo.get_driver_risk(driver_id)

    def process_telemetry_and_risk(self, telemetry_update: Dict[str, Any]) -> Dict[str, Any]:
        """Ingests live telemetry frame, computes/updates risk status, and records anomalies."""
        return self.repo.update_driver_risk_and_telemetry(telemetry_update)

    def create_risk_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Records an explicit alert event into the persistent event log."""
        return self.repo.add_event(event_data)

    def list_alerts(
        self,
        limit: int = 50,
        severity: Optional[str] = None,
        driver_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return self.repo.get_alerts(limit=limit, severity=severity, driver_id=driver_id)


_risk_service_instance: Optional[RiskService] = None


def get_risk_service() -> RiskService:
    global _risk_service_instance
    if _risk_service_instance is None:
        _risk_service_instance = RiskService()
    return _risk_service_instance
