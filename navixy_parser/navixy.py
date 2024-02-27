import datetime
import json
import logging
import sys
from typing import Optional

import requests
from dataclasses import dataclass
from navixy_parser import config

@dataclass
class TrackStatus:
    id: int
    label: str
    color: str
    changed: datetime.datetime


@dataclass
class TrackSource:
    id: int
    device_id: int
    model: str
    blocked: bool
    tariff_id: int
    phone: str
    status_listing_id: int
    creation_date: datetime.datetime
    tariff_end_date: datetime.datetime


@dataclass
class Track:
    id: int
    label: str
    group_id: int
    source: TrackSource
    clone: bool


@dataclass
class TrackLocation:
    address: str
    lat: float
    lng: float


@dataclass
class JournalRecord:
    tracker_id: int
    employee_id: Optional[int]
    start_date: datetime.datetime
    end_date: datetime.datetime
    length: float
    start_location: TrackLocation
    end_location: TrackLocation
    # start_odometer: null,
    # end_odometer: null,
    overlapped: bool


@dataclass
class TripDetection:
    min_idle_duration_minutes: int
    idle_speed_threshold: int
    ignition_aware: bool
    motion_sensor_aware: bool


@dataclass
class TrackHistory:
    id: int
    start_date: datetime.datetime
    end_date: datetime.datetime
    avg_speed: float
    max_speed: float
    length: float
    start_address: str
    end_address: str



class Tag:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


class TrackTagBindings:
    def __init__(self, tag_id: int, ordinal: int):
        self.tag_id = tag_id
        self.ordinal = ordinal


def unpack_tag_value(tag_ordinal: int, tags_list: list[Tag], tag_bindings: list[TrackTagBindings]) -> str:
    for track_tags in tag_bindings:
        if track_tags.ordinal == tag_ordinal:
            for tag in tags_list:
                if tag.id == track_tags.tag_id:
                    return tag.name






class Client():
    api_url = "https://api.fleetcontrolsol.com/"
    hash: str | None = "None"
    login = config.login
    password = config.password

    def __init__(self):
        logging.info('Starting navixy parser')
        # self.hash = self.get_hash()


    def get_hash(self) -> str:
        endpoint_path = f'user/auth?password={self.password}&login={self.login}'
        resp = requests.get(self.api_url + endpoint_path)
        if resp.status_code == 200:
            logging.info('Success logged in and get fresh hash')
            return resp.json()['hash']
        else:
            logging.error(f'Error while trying to get hash! Error: {resp.text} ({resp.status_code})')
            sys.exit(1)

    def get_all_tags(self) -> list[Tag]:

        logging.info('Start trying to get all tags data')

        endpoint_path = f'tag/list?hash={self.hash}'
        headers = {
            'Content-Type': 'application/json'
        }
        resp = requests.get(self.api_url + endpoint_path, headers=headers)

        if resp.status_code == 200:
            logging.info('Success get tags list unpacking started')

            return [Tag(tag['id'], tag['name']) for tag in resp.json()['list']]
        else:
            logging.error(f'Error while trying to get tags list! Error: {resp.text} ({resp.status_code})')
            sys.exit(1)


    def get_all_tracks_with_tag_bindings(self):
        endpoint_path = f"tracker/list?hash={self.hash}"
        response = requests.get(self.api_url + endpoint_path, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            tracks = []
            tag_bindings = []
            
            for item in data['list']:
                # Construct Track object (as previously defined)
                track = Track(
                    id=item['id'],
                    label=item['label'],
                    group_id=item['group_id'],
                    source=TrackSource(
                        id=item['source']['id'],
                        device_id=item['source']['device_id'],
                        model=item['source']['model'],
                        blocked=item['source']['blocked'],
                        tariff_id=item['source']['tariff_id'],
                        phone=item['source']['phone'],
                        status_listing_id=item['source']['status_listing_id'],
                        creation_date=datetime.datetime.strptime(item['source']['creation_date'], "%Y-%m-%d"),
                        tariff_end_date=datetime.datetime.strptime(item['source']['tariff_end_date'], "%Y-%m-%d"),
                    ),
                    clone=item['clone']
                )
                tracks.append(track)

                # Process Tag Bindings for the current tracker
                for binding in item.get('tag_bindings', []):
                    tag_binding = TrackTagBindings(tag_id=binding['tag_id'], ordinal=binding['ordinal'])
                    tag_bindings.append(tag_binding)

            return tracks, tag_bindings
        else:
            logging.error(f"Failed to fetch tracks and tag bindings: {response.text}")
            return [], []


    def get_all_tracks(self):
        #  -> list[Track]
        logging.info('Start trying to get all tracks data')

        endpoint_path = f'tracker/list?hash={self.hash}'

        resp = requests.get(self.api_url + endpoint_path, verify=False)
        if resp.status_code != 200:
            logging.error(f'Error while trying to get tracks list! Error: {resp.text} ({resp.status_code})')
            sys.exit(1)

        logging.info(f'Success get all basic tracks data - start unboxing')
        return [Track(track['id'], track['label'], track['group_id'],
                      TrackSource(track['source']['id'], int(track['source']['device_id']), track['source']['model'],
                                  track['source']['blocked'], track['source']['tariff_id'],
                                  track['source']['phone'], track['source']['status_listing_id'],
                                  datetime.datetime.strptime(track['source']['creation_date'], "%Y-%m-%d"),
                                  datetime.datetime.strptime(track['source']['tariff_end_date'], "%Y-%m-%d")),
                      track['clone'])
                for track in resp.json()['list']]

    def get_status(self):
        '/status/listing/list'
        ...

    def get_driver_journal(self, tracker_id, time_to=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           time_from=(datetime.datetime.now() - datetime.timedelta(days=60)).strftime(
                               "%Y-%m-%d %H:%M:%S")):
        # -> list[JournalRecord]

        endpoint_path = f"driver/journal/proposal/list?hash={self.hash}" \
                        f"&tracker_id={tracker_id}" \
                        f"&from={time_from}&to={time_to}"

        response = requests.get(self.api_url + endpoint_path, verify=False)

        if response.status_code != 200:
            logging.error(f'Error while trying to get tracks journal data list! '
                          f'Error: {response.text} ({response.status_code})')
            sys.exit(1)

        return [JournalRecord(journal_records['tracker_id'],
                              journal_records['employee_id'],
                              datetime.datetime.strptime(journal_records['start_date'], "%Y-%m-%d %H:%M:%S"),
                              datetime.datetime.strptime(journal_records['end_date'], "%Y-%m-%d %H:%M:%S"),
                              journal_records['length'],
                              TrackLocation(journal_records['start_location']['address'],
                                            journal_records['start_location']['lat'],
                                            journal_records['start_location']['lng']),
                              TrackLocation(journal_records['end_location']['address'],
                                            journal_records['end_location']['lat'],
                                            journal_records['end_location']['lng']), journal_records['length']) for
                journal_records in response.json()['list']]

    def get_trip_detection_data(self, tracker_id):
        endpoint_path = f"tracker/settings/trip_detection/read?hash={self.hash}&tracker_id={tracker_id}"

        response = requests.get(self.api_url + endpoint_path, verify=False)

        if response.status_code != 200:
            logging.error(f'Error while trying to get track ({tracker_id}) trip_detection! '
                          f'Error: {response.text} ({response.status_code})')
            sys.exit(1)
        detection_data = response.json()
        return TripDetection(detection_data['min_idle_duration_minutes'], detection_data['idle_speed_threshold'],
                             detection_data['ignition_aware'], detection_data['motion_sensor_aware'])

    def get_track_history(self, tracker_id, time_to=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           time_from=(datetime.datetime.now() - datetime.timedelta(days=60)).strftime(
                               "%Y-%m-%d %H:%M:%S")):
        #  -> list[TrackHistory]

        endpoint_path = f"track/list/?hash={self.hash}" \
                        f"&tracker_id={tracker_id}" \
                        f"&from={time_from}&to={time_to}"

        response = requests.get(self.api_url + endpoint_path, verify=False)

        if response.status_code != 200:
            logging.error(f'Error while trying to get track ({tracker_id}) history journal! '
                          f'Error: {response.text} ({response.status_code})')
            sys.exit(1)



        return [TrackHistory(history_records['id'],
                             datetime.datetime.strptime(history_records['start_date'], "%Y-%m-%d %H:%M:%S"),
                             datetime.datetime.strptime(history_records.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')), "%Y-%m-%d %H:%M:%S"),
                             history_records.get('length', 0), history_records.get('avg_speed', 0),
                             history_records.get('max_speed', 0), history_records['start_address'],
                             history_records.get('end_address')) for
                history_records in response.json()['list']]

    def get_track_status(self, tracker_id):
        #  -> Optional[TrackStatus]

        endpoint_path = f'status/tracker/read?hash={self.hash}&tracker_id={tracker_id}'
        response = requests.get(self.api_url + endpoint_path, verify=False)

        if response.status_code != 200:
            logging.error(f'Error while trying to get track ({tracker_id}) status! '
                          f'Error: {response.text} ({response.status_code})')
            sys.exit(1)

        status = response.json()
        if status.get('current_status') is None:
            return None

        return TrackStatus(status['current_status'].get('id'), status['current_status'].get('label'),
                           status['current_status'].get('color'), datetime.datetime.strptime(status['last_change']['changed'],
                                                                                         "%Y-%m-%d %H:%M:%S"))

    def get_zone(self, lat, lng):
        coord_data = json.dumps({"lat": lat, "lng": lng})

        endpoint_path = f'zone/search_location/?hash={self.hash}&location={coord_data}'
        response = requests.get(self.api_url + endpoint_path, verify=False)

        if response.status_code != 200:
            logging.error(f'Error while trying to get zone_list! '
                          f'Error: {response.text} ({response.status_code})')
            sys.exit(1)
        try:
            return response.json()['list'][0]['label']
        except IndexError:
            return None


   

