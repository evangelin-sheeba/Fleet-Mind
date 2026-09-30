"""
Database service wrapping repository queries and data transformation.
"""

from typing import List, Optional, Dict, Any
from app.database.json_repository import JSONRepository, get_repository


class DatabaseService:
    def __init__(self, repo: Optional[JSONRepository] = None):
        self.repo = repo or get_repository()

    def list_drivers(self, status: Optional[str] = None, risk_level: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.get_all_drivers(status=status, risk_level=risk_level)

    def get_driver_by_id(self, driver_id: str) -> Optional[Dict[str, Any]]:
        return self.repo.get_driver(driver_id)

    def list_vehicles(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.repo.get_all_vehicles(status=status)

    def get_vehicle_by_id(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        return self.repo.get_vehicle(vehicle_id)

    def get_fleet_status(self) -> Dict[str, Any]:
        return self.repo.get_fleet_summary()

    def record_manager_command(self, cmd_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.repo.add_command(cmd_data)

    def list_manager_commands(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.repo.get_commands(limit=limit)


_db_service_instance: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    global _db_service_instance
    if _db_service_instance is None:
        _db_service_instance = DatabaseService()
    return _db_service_instance
