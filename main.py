from flask import Flask, request, render_template, url_for, redirect, send_file
import datetime
import pandas as pd
import os
import threading
from utils import excel 
from navixy_parser.navixy import Client, JournalRecord, TrackHistory, Tag, TrackTagBindings, TrackStatus
from navixy_parser import events
from navixy_parser.events import Event

app = Flask(__name__)

@app.route('/')
def index():
        
    navixy_client = Client()

    tracks = navixy_client.get_all_tracks()
    
    return render_template('index.html', tracks=tracks)

@app.route('/header1', methods=['POST'])
def header1():
    button_clicked = request.form['time_period']
    track_id = request.form['track_id']
    track_label = request.form['track_label']
    now = datetime.datetime.now()

    if button_clicked == '24_hours':
        start_date = now - datetime.timedelta(days=1)
        end_date = now
    elif button_clicked == '1_week':
        start_date = now - datetime.timedelta(weeks=1)
        end_date = now
    else:
        # Custom time period selected
        start_date = request.form['start_date']
        end_date = request.form['end_date']
    
    tracks = return_track_array(track_id, track_label, [], start_date.strftime("%Y-%m-%d %H:%M:%S"), end_date.strftime("%Y-%m-%d %H:%M:%S"))

    if len(tracks) > 0:
        print("tracks..........")
        print(tracks)
        print("================")
        save_file = excel.export_data(tracks)
        return send_file(save_file, as_attachment=True)
    else:
        return redirect(url_for('index'))

@app.route('/header1/download/loading/<int:download_link_id>')
def download_loading(download_link_id):
    download_link = getattr(threading.local(), f'download_link_{download_link_id}', None)
    if download_link is None:
        return 'File not found'
    else:
        return render_template('download.html', download_link=download_link.get())

@app.route('/header1/download')
def download():
    filename = request.args.get('filename')
    file_path = os.path.join(app.root_path, "static", filename)
    if os.path.exists(file_path):
        return redirect(url_for('static', filename=filename, _external=True))
    else:
        return 'File not found'

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

def return_track_array(track_id, track_label, tag_bindings, time_from, time_to):

    print('Start creating client')
    navixy_client = Client()
    tags_data = navixy_client.get_all_tags()

    events = []
    event = {}

    print('Parsing starting')

    track_journal_data = navixy_client.get_driver_journal(track_id, time_to, time_from)
    trip_detection_data = navixy_client.get_trip_detection_data(track_id)
    track_history_data = navixy_client.get_track_history(track_id, time_to, time_from)
    track_status = navixy_client.get_track_status(track_id)

    for journal_record in track_journal_data:
        for history_data in track_history_data:
            event = {}
            if history_data_to_driver_journal_data(history_data, journal_record):
                start_zone = navixy_client.get_zone(journal_record.start_location.lat,
                                                journal_record.start_location.lng)
                end_zone = navixy_client.get_zone(journal_record.end_location.lat,
                                                    journal_record.end_location.lng)
                event["record_id"] = history_data.id
                event["track_id"] = track_id
                event["track_label"] = track_label
                event["time_start"] = journal_record.start_date.strftime("%Y-%m-%d %H:%M:%S")
                event["time_end"] = journal_record.end_date.strftime("%Y-%m-%d %H:%M:%S")
                event["from_address"] = journal_record.start_location.address
                event["to_address"] = journal_record.end_location.address
                event["distance"] = journal_record.length
                event["duration"] = create_duration(journal_record)
                event["max_speed"] = history_data.max_speed
                event["Driver"] = journal_record.employee_id
                event["TT_number_tags"] = unpack_tag_value(1, tags_data, tag_bindings)
                event["Registration_plate"] = unpack_tag_value(2, tags_data, tag_bindings)
                event["Product"] = unpack_tag_value(3, tags_data, tag_bindings)
                event["Parked"] = trip_detection_data.ignition_aware
                event["Idle_time"] = trip_detection_data.min_idle_duration_minutes
                event["status"] = get_track_status(track_status, journal_record)
                event["zone"] = f"{start_zone} > {end_zone}"

                events.append(event)
                print(f'Data from date {journal_record.start_date} for track {track_id} recorded')
    print('Iteration done, sleep 15 sec')

    return events


if __name__ == '__main__':
    app.run()
