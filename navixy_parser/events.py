import datetime
from dataclasses import dataclass


@dataclass
class Event:
    track_id: int
    track_label: str
    time_start: datetime.datetime
    time_end: datetime.datetime
    from_address: str
    to_address: str
    zone: str
    distance: float
    duration: str
    max_speed: float
    Parked: bool
    Idle_time: float
    Driver: int
    TT_number_tags: str
    Registration_plate: str
    Product: str
    status: str