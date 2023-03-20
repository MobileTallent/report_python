from flask import Flask, request, render_template, url_for, redirect, send_file
import datetime
import pandas as pd
from utils import filemaker 
from navixy_parser.navixy import Client, JournalRecord, TrackHistory, Tag, TrackTagBindings, TrackStatus

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
        start_date = now - datetime.timedelta(days=1).strftime("%Y-%m-%d 00:00:00")
        end_date = now.strftime("%Y-%m-%d 23:59:59")
    elif button_clicked == '1_week':
        start_date = now - datetime.timedelta(weeks=1).strftime("%Y-%m-%d 00:00:00")
        end_date = now.strftime("%Y-%m-%d 23:59:59")
    else:
        # Custom time period selected
        start_date = datetime.datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.datetime.strptime(request.form['end_date'], '%Y-%m-%d')
    
    tracks = return_track_array(track_id, track_label, [], start_date, end_date)

    if len(tracks) > 0:
        save_file = filemaker.export_data1(tracks)
        return send_file(save_file, as_attachment=True)
    else:
        print("There is no raw data to be exported")
        return redirect(url_for('index'))

@app.route('/header2', methods=['POST'])
def header2():
    start_date = datetime.datetime.strptime(request.form['start_date'], '%Y-%m-%d')
    end_date = datetime.datetime.strptime(request.form['end_date'], '%Y-%m-%d')
    track_id = request.form['track_id']
    track_label = request.form['track_label']

    tracks = return_track_array(track_id, track_label, [], start_date, end_date)

    save_file = filemaker.export_data2(tracks, track_label, start_date, end_date)
    
    return send_file(save_file, as_attachment=True)


@app.route('/header3', methods=['POST'])
def header3():
    track_id = request.form['track_id']
    track_label = request.form['track_label']
    start_date = datetime.datetime.strptime(request.form['start_date'], '%Y-%m-%d')
    end_date = datetime.datetime.strptime(request.form['end_date'], '%Y-%m-%d')

    tracks = return_track_array(track_id, track_label, [], start_date, end_date)

    save_file = filemaker.export_data3(tracks)

    return send_file(save_file, as_attachment=True)



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
