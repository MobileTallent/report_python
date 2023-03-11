import time

from navixy_parser.navixy import Client, JournalRecord, TrackHistory, Tag, TrackTagBindings, TrackStatus
from navixy_parser import events
from navixy_parser.events import Event
import logging

logging.basicConfig(level=logging.INFO, format='%(filename)s: %(asctime)s - %(name)s - %(levelname)s - %(message)s')


def history_data_to_driver_journal_data(history_data: TrackHistory, journal_record: JournalRecord):
    """
    history data and journal record data comparator
    :param history_data:
    :param journal_record:
    :return:
    """
    if history_data.start_date == journal_record.start_date and \
        history_data.end_date == journal_record.end_date and \
        history_data.start_address == journal_record.start_location.address and \
        history_data.end_address == journal_record.end_location.address:
        return True
    return False


def create_duration(journal_record: JournalRecord) -> str:
    """
    generating timedelta for track move duration and convert into string
    :param journal_record:
    :return:
    """
    return str(journal_record.end_date - journal_record.start_date)


def unpack_tag_value(tag_ordinal: int, tags_list: list[Tag], tag_bindings: list[TrackTagBindings]) -> str:
    """
    getting tag value
    """
    for track_tags in tag_bindings:
        if track_tags.ordinal == tag_ordinal:
            for tags in tags_list:
                if tags.id == track_tags.tag_id:
                    return tags.name
    return ''


def get_track_status(track_status: TrackStatus, journal_record: JournalRecord):
    if track_status is None:
        return None
    status_result = track_status.label if journal_record.start_date <= track_status.changed else None
    return status_result

def return_track_array():

    logging.info('Start creating client')
    navixy_client = Client()
    tags_data = navixy_client.get_all_tags()

    logging.info('Parsing starting')

    for track in navixy_client.get_all_tracks():
        track_journal_data = navixy_client.get_driver_journal(track.id)
        trip_detection_data = navixy_client.get_trip_detection_data(track.id)
        track_history_data = navixy_client.get_track_history(track.id)
        track_status = navixy_client.get_track_status(track.id)

        for journal_record in track_journal_data:
            for history_data in track_history_data:
                if history_data_to_driver_journal_data(history_data, journal_record):
                    start_zone = navixy_client.get_zone(journal_record.start_location.lat,
                                                    journal_record.start_location.lng)
                    end_zone = navixy_client.get_zone(journal_record.end_location.lat,
                                                        journal_record.end_location.lng)
                    event = Event(track_id=track.id,
                                    track_label=track.label,
                                    time_start=journal_record.start_date,
                                    time_end=journal_record.end_date,
                                    from_address=journal_record.start_location.address,
                                    to_address=journal_record.end_location.address,
                                    distance=journal_record.length,
                                    duration=create_duration(journal_record),
                                    max_speed=history_data.max_speed,
                                    Driver=journal_record.employee_id,
                                    TT_number_tags=unpack_tag_value(1, tags_data, track.tag_bindings),
                                    Registration_plate=unpack_tag_value(2, tags_data, track.tag_bindings),
                                    Product=unpack_tag_value(3, tags_data, track.tag_bindings),
                                    Parked=trip_detection_data.ignition_aware,
                                    Idle_time=trip_detection_data.min_idle_duration_minutes,
                                    status=get_track_status(track_status, journal_record),
                                    zone=f"{start_zone} > {end_zone}")

                    events.add_new(event)
                    logging.info(f'Data from date {journal_record.start_date} for track {track.id} recorded')
    logging.info('Iteration done, sleep 15 sec')

    return events