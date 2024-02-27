from flask import Flask, request, render_template, url_for, redirect, send_file
import datetime
from utils import filemaker 
from navixy_parser.navixy import Client, JournalRecord, TrackHistory, TrackStatus, unpack_tag_value, Tag, TrackTagBindings
from flask_apscheduler import APScheduler
import requests
import pandas as pd
import logging
import urllib3
from flask_mail import Mail, Message

app = Flask(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)





# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.fleetcontrolsol.com'  # Replace with your mail server
app.config['MAIL_PORT'] = '465'
app.config['MAIL_USERNAME'] = 'admin@fleetcontrolsol.com'
app.config['MAIL_PASSWORD'] = 'G30rge@Kingsw00d48'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
 
mail = Mail(app)



class Client2:
    def __init__(self):
        self.hash = None

    def authenticate(self, username, password):
        auth_url = 'https://api.fleetcontrolsol.com/user/auth'
        payload = {'login':'pierre@acuit.co.za' , 'password':'P@ssw321*'}
        response = requests.post(auth_url, json=payload)

        if response.ok:
            data = response.json()
            if data['success']:
                self.hash = data['hash']  # Assuming 'hash' is the session key
                return True
        return False



ui_navixy_client = Client()
reports_navixy_client = Client2()

reports_client = Client2()
if reports_client.authenticate('username_for_reports', 'password_for_reports'):
    reports_hash = reports_client.hash
else:
    reports_hash = None


# Initialize scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()







@app.route('/test_email')
def test_email_route():
    return test_email()

def test_email():
    try:
        with app.app_context():
            # Create a test message
            msg = Message("Test Email", sender=app.config['MAIL_USERNAME'], recipients=["pierrevanrensburg12@gmail.com"])
            msg.body = "This is a test email sent from Flask app to check email configuration."
            
            # Send the email
            mail.send(msg)
            return "Email sent successfully!"
    except Exception as e:
        # If something goes wrong, print the exception
        return f"Failed to send email: {e}"


@app.route('/')
def index():
    session_key = request.args.get('session_key')

    navixy_client = Client()

    if session_key:
        navixy_client.hash = session_key

        tracks = navixy_client.get_all_tracks()
    
        return render_template('index.html', tracks=tracks, session_key=session_key)
    else:
        return render_template('error.html')


@app.route('/header1', methods=['POST'])
def header1():
    button_clicked = request.form['time_period']
    track_id = request.form['track_id']
    track_label = request.form['track_label']
    session_key = request.form['session_key']
    now = datetime.datetime.now()

    if button_clicked == '24_hours':
        start_date = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
        end_date = now.strftime("%Y-%m-%d 23:59:59")

        tracks = return_track_array(track_id, track_label, start_date, end_date, session_key)
    elif button_clicked == '1_week':
        start_date = (now - datetime.timedelta(weeks=1)).strftime("%Y-%m-%d 00:00:00")
        end_date = now.strftime("%Y-%m-%d 23:59:59")

        tracks = return_track_array(track_id, track_label, start_date, end_date, session_key)
    else:

        if request.form['start_date'] and request.form['end_date']:
            # Custom time period selected
            start_date = datetime.datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = datetime.datetime.strptime(request.form['end_date'], '%Y-%m-%d')

            tracks = return_track_array(track_id, track_label, start_date, end_date, session_key)
        else:
            tracks = []
    
    if len(tracks) > 0:
        save_file = filemaker.export_data1(tracks)
        return send_file(save_file, as_attachment=True)
    else:
        print("There is no raw data to be exported")
        return redirect(url_for('index', session_key=session_key))



def generate_report_header1(time_period):
    # Removed track_id and track_label as they are no longer needed
    session_key = reports_hash
    now = datetime.datetime.now()

    if time_period == '24_hours':
        start_date = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
        end_date = now.strftime("%Y-%m-%d 00:59:59")
    elif time_period == '1_week':
        start_date = (now - datetime.timedelta(weeks=1)).strftime("%Y-%m-%d 00:00:00")
        end_date = now.strftime("%Y-%m-%d 23:59:59")
    # Add more time periods if needed

    # Call a modified version of return_track_array that handles all tracks
    tracks = return_all_tracks_array(start_date, end_date, session_key)
    
    if len(tracks) > 0:
        # Populate template and return the rendered content
        rendered_content = render_template('report_template.html', tracks=tracks)
        return rendered_content
    else:
        return None

def return_all_tracks_array(start_date, end_date, session_key):
    # Initialize the client with the session key
    navixy_client = Client()
    navixy_client.hash = session_key

    all_tracks = []  # List to store information of all tracks

    # Get all track IDs and their labels
    all_track_ids = navixy_client.get_all_tracks()

    for track in all_track_ids:
        track_id = track.id
        track_label = track.label
        track_data = return_track_array(track_id, track_label, start_date, end_date, session_key)
        all_tracks.extend(track_data)  # Add data of each track to the list

    return all_tracks





@app.route('/download_report')
def download_report():
    try:
        session_key = reports_hash  # or however you obtain the session key
        navixy_client = Client()
        navixy_client.hash = session_key

        # Fetch data
        now = datetime.datetime.now()
        start_date = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")
        end_date = now.strftime("%Y-%m-%d 23:59:59")
        track_ids = navixy_client.get_all_tracks()

        tracks = return_tracks_array1(navixy_client, track_ids, start_date, end_date)

        # Generate Excel report
        filename = '/mnt/data/Report.xlsx'  # Ensure this directory exists and is writable
        generate_excel_report(tracks, filename)

        return send_file(filename, as_attachment=True)
    except Exception as e:
        return str(e)

def send_report_email(report_type, report_content):
    subject = f"Report: {report_type}"
    recipients = ["pierre@acuit.co.za"]  # Add your recipient list here

    with app.app_context():
        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=recipients)
        msg.html = report_content  # HTML content from the template

        # Send email
        mail.send(msg)


def generate_report_file(time_period):
    session_key = reports_hash
    now = datetime.datetime.now()

    # Define start and end dates based on time_period
    if time_period == '24_hours':
        start_date = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
        end_date = now.strftime("%Y-%m-%d 23:59:59")
    # Add more time periods if needed

    tracks = return_all_tracks_array(start_date, end_date, session_key)
    
    if len(tracks) > 0:
        # Use the appropriate function from filemaker to generate the file
        save_file = filemaker.export_dataX(tracks)  # Replace export_dataX with actual function
        return save_file
    else:
        return None
    






def generate_excel_report(data, filename):
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(data)
    
    # List of columns to exclude
    columns_to_exclude = ['record_id', 'track_id', 'Parked', 'Idle_time']
    
    # Drop the unwanted columns
    df = df.drop(columns=columns_to_exclude, errors='ignore')
    
    # Save the remaining DataFrame to an Excel file
    df.to_excel(filename, index=False)





## Example: Send header1 report for the last 24 hours
#@scheduler.task('cron', id='daily_header1_report', hour=21, minute=0)
#def send_daily_header1_report():
#    report_content = generate_report_header1('24_hours')
 #   if report_content:
  #      send_report_email('Header1 Daily', report_content)

# Similar scheduling for other time periods




def send_report_with_excel():
    try:
        print("Scheduled task started - send_report_with_excel")
        session_key = reports_hash  # Ensure this is the correct session key
        navixy_client = Client()
        navixy_client.hash = session_key

        # Fetch data for the report
        now = datetime.datetime.now()
        start_date = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
        end_date = now.strftime("%Y-%m-%d 23:59:59")
        track_ids = navixy_client.get_all_tracks()

        tracks = return_tracks_array1(navixy_client, track_ids, start_date, end_date)

        # Generate Excel report
        filename = '/mnt/data/report.xlsx'
        generate_excel_report(tracks, filename)
        print("Report generated, sending email...")


        # Email the report as an attachment
        send_report_email_with_attachment1('Daily Report', 'Please find the attached report.', filename)

    except Exception as e:
        app.logger.error(f'Error in send_report_with_excel: {e}')



def send_report_email_with_attachment1(subject, body, attachment_filename):
    print("Preparing to send email with attachment...")
    recipients = ["pierre@acuit.co.za"]  # Replace with actual recipients
    msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=recipients)
    msg.body = body

    try:
        with app.open_resource(attachment_filename) as fp:
            msg.attach("Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fp.read())
        print("Attachment added, sending email...")
        mail.send(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Schedule the daily report email task
#scheduler.add_job(id='send_daily_excel_report', func=send_report_with_excel, trigger='cron', hour=21, minute=0)
###########################################################

@app.route('/email_report')
def email_report():
    try:
        logging.info("Email report requested")

        session_key = reports_hash
        navixy_client = Client()
        navixy_client.hash = session_key
 
        now = datetime.datetime.now()
        start_date = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        end_date = now.strftime("%Y-%m-%d %H:%M:%S")

        # Fetch all tracks for the time period
        track_objects = navixy_client.get_all_tracks()  # This returns a list of Track objects

        all_tracks_data = []

        # Iterate through each Track object
        for track_obj in track_objects:
            track_id = track_obj.id  # Use dot notation to access the id attribute
            track_label = getattr(track_obj, 'label', 'Unknown Label')  # Use getattr to handle missing 'label' safely

            # Fetch data for each track using the corrected attribute access
            track_data = return_track_array(track_id, track_label, start_date, end_date, session_key)
            all_tracks_data.extend(track_data)

        # Generate Excel report
        filename = '/mnt/data/Report.xlsx'
        generate_excel_report(all_tracks_data, filename)

        # Email the report as an attachment
        subject = "Weekly Report"
        body = "Please find the attached weekly report."
        recipients = ["recipient@example.com"]  # Ensure this uses actual recipient addresses
        send_report_email_with_attachment(subject, body, filename, recipients)

        logging.info("Report email sent successfully")
        return "Email sent successfully"
    except Exception as e:
        logging.error(f"Error in email_report: {e}")
        return str(e)

def send_report_email_with_attachment(subject, body, attachment_filename, recipients):
    try:
        recipients = ["pierrevanrensburg12@gmail.com","deon@fleetcontrolsol.com","deonm2m@gmail.com"]  # Replace with actual recipients
        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=recipients)
        msg.body = body

        with app.open_resource(attachment_filename) as fp:
            msg.attach("Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fp.read())

        mail.send(msg)
        logging.info("Email with attachment sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email with attachment: {e}")


def scheduled_email_report():
    with app.app_context():
        try:
            logging.info("Scheduled email report started")

            session_key = reports_hash
            navixy_client = Client()
            navixy_client.hash = session_key

            now = datetime.datetime.now()
            start_date = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")
            end_date = now.strftime("%Y-%m-%d 23:59:59")

            track_infos = navixy_client.get_all_tracks()  # Assuming this returns a list of track objects or identifiers

            all_tracks_data = []

            for track_info in track_infos:
                track_id = track_info.id  # Adjust based on the actual structure
                track_label = getattr(track_info, 'label', 'Unknown')  # Default label if not present

                track_data = return_track_array(track_id, track_label, start_date, end_date, session_key)
                all_tracks_data.extend(track_data)

            filename = '/mnt/data/Report.xlsx'
            generate_excel_report(all_tracks_data, filename) 

            # Email the report as an attachment
            subject = "Scheduled Weekly Report"
            body = "Please find the attached weekly report."
            recipients = ["pierrevanrensburg12@gmail.com","deon@fleetcontrolsol.com"] 
            send_report_email_with_attachment(subject, body, filename, recipients)

            logging.info("Scheduled email report sent successfully")
        except Exception as e:
            logging.error(f"Error in scheduled_email_report: {e}")

scheduler.add_job(id='scheduled_email_report', func=scheduled_email_report, trigger='cron', hour=20, minute=5)






########################################################################################################################











@app.route('/header2', methods=['POST'])
def header2():

    session_key = request.form['session_key']
    
    if request.form['start_date'] and request.form['end_date']:

        start_date = datetime.datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        track_id = request.form['track_id']
        track_label = request.form['track_label']
        

        tracks = return_track_array(track_id, track_label, start_date, end_date, session_key)

        save_file = filemaker.export_data2(tracks, track_label, start_date, end_date)
        
        return send_file(save_file, as_attachment=True)
    else:
        return redirect(url_for('index', session_key=session_key))


@app.route('/header3', methods=['POST'])
def header3():

    session_key = request.form['session_key']
    
    if request.form['start_date'] and request.form['end_date']:

        track_id = request.form['track_id']
        track_label = request.form['track_label']
        start_date = datetime.datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.datetime.strptime(request.form['end_date'], '%Y-%m-%d')

        tracks = return_track_array(track_id, track_label, start_date, end_date, session_key)

        save_file = filemaker.export_data3(tracks)

        return send_file(save_file, as_attachment=True)
    else:
        return redirect(url_for('index', session_key=session_key))

@app.route('/header4', methods=['POST'])
def header4():

    session_key = request.form['session_key']
    now = datetime.datetime.now()
    
    start_date = (now - datetime.timedelta(days=4)).strftime("%Y-%m-%d 00:00:00")
    end_date = now.strftime("%Y-%m-%d 23:59:59")

    navixy_client = Client()

    if session_key:
        navixy_client.hash = session_key

        track_ids = navixy_client.get_all_tracks()

        tracks = return_tracks_array1(navixy_client, track_ids, start_date, end_date)

        save_file = filemaker.export_data4(tracks)

        return send_file(save_file, as_attachment=True)

    else:
        return render_template('error.html')


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


def get_track_status(track_status: TrackStatus, journal_record: JournalRecord):
    if track_status is None:
        return None
    status_result = track_status.label if journal_record.start_date <= track_status.changed else None
    return status_result


def return_tracks_array1(navixy_client, track_ids, time_from, time_to):
    print('Start creating client')

    events = []

    for track in track_ids:
        track_id = track.id
        track_label = track.label

        track_journal_data = navixy_client.get_driver_journal(track_id, time_to, time_from)

        event = {}

        if len(track_journal_data) > 0:
            journal_record = track_journal_data[len(track_journal_data) - 1]

            event["track_id"] = track_id
            event["track_label"] = track_label
            event["time_start"] = journal_record.start_date.strftime("%Y-%m-%d %H:%M:%S")
            event["time_end"] = journal_record.end_date.strftime("%Y-%m-%d %H:%M:%S")
            event["from_address"] = journal_record.start_location.address
            event["to_address"] = journal_record.end_location.address
            event["duration"] = create_duration(journal_record)

            events.append(event)
            print(f'Data from date {journal_record.start_date} for track {track_id} recorded')
        print('Iteration done, sleep 15 sec')

    return events

def return_track_array(track_id, track_label, time_from, time_to, session_key):

    print('Start creating client')
    navixy_client = Client()

    navixy_client.hash = session_key

    events = []
    event = {}

    print('Parsing starting')

    track_journal_data = navixy_client.get_driver_journal(track_id, time_to, time_from)
    trip_detection_data = navixy_client.get_trip_detection_data(track_id)
    track_history_data = navixy_client.get_track_history(track_id, time_to, time_from)
    tags_data = navixy_client.get_all_tags()
    tag_bindings = navixy_client.get_all_tracks_with_tag_bindings()

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
                event["zone"] = f"{start_zone} > {end_zone}"

                events.append(event)
                print(f'Data from date {journal_record.start_date} for track {track_id} recorded')
    print('Iteration done, sleep 15 sec')

    return events


if __name__ == '__main__':
    app.run(debug=True)
