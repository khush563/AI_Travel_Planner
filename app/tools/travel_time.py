from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TravelEstimate:
    origin: str
    destination: str
    distance_km: float
    minutes: int
    note: str = "Approximate planning estimate; verify routes before travel."


class TravelTimeProvider(Protocol):
    def estimate(self, origin: str, destination: str, origin_area: str = "", destination_area: str = "") -> TravelEstimate: ...


class ApproximateTravelTime:
    """Replaceable local estimate when a routing API is unavailable."""

    def estimate(self, origin: str, destination: str, origin_area: str = "", destination_area: str = "") -> TravelEstimate:
        if origin.strip().casefold() == destination.strip().casefold():
            distance, minutes = 0.0, 0
        elif origin_area and destination_area and origin_area.casefold() == destination_area.casefold():
            distance, minutes = 2.0, 15
        else:
            distance, minutes = 8.0, 40
        return TravelEstimate(origin, destination, distance, minutes)

