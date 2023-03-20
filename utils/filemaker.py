import os
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd
import docx
import matplotlib.pyplot as plt
import numpy as np
import datetime
import time

APP_ROOT = os.path.dirname(os.path.abspath(__file__))   # refers to application_top
save_file1 = os.path.join(APP_ROOT, '../download/header1/data.xlsx')
save_file2 = os.path.join(APP_ROOT, '../download/header2/data.docx')
save_file3 = os.path.join(APP_ROOT, '../download/header3/data.docx')

def export_data1(tracks):
    """Save and Export one file in excel worksheet and """

    wb = openpyxl.load_workbook(filename=save_file1)
    ws = wb['Sheet1']

    for row in ws.iter_rows(min_row=2, max_col=10):
        for cell in row:
            cell.value = None

    for row_index in range(len(tracks)):
        row_num = str(row_index + 2)
        row = tracks[row_index]

        ws['A' + row_num].value = row['record_id']
        ws['B' + row_num].value = row['track_id']
        ws['C' + row_num].value = row['track_label']
        ws['D' + row_num].value = row['time_start']
        ws['E' + row_num].value = row['time_end']
        ws['F' + row_num].value = row['from_address']
        ws['G' + row_num].value = row['to_address']
        ws['H' + row_num].value = row['distance']
        ws['I' + row_num].value = row['duration']
        ws['J' + row_num].value = row['max_speed']
        ws['K' + row_num].value = row['Driver']
        ws['L' + row_num].value = row['TT_number_tags']
        ws['M' + row_num].value = row['Registration_plate']
        ws['N' + row_num].value = row['Product']
        ws['O' + row_num].value = row['Parked']
        ws['P' + row_num].value = row['Idle_time']
        ws['Q' + row_num].value = row['status']
        ws['R' + row_num].value = row['zone']

    wb.save(filename=save_file1)

    return save_file1

def export_data2(tracks, track_label, start_date, end_date):
    # create a new Word document
    doc = docx.Document()

    # add a heading to the document
    doc.add_heading('Utilization Report', 0)
    doc.add_paragraph(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' Africa/Luburrbashi')
    doc.add_paragraph('Assets: any Vehicle')
    doc.add_paragraph('From: ' + start_date.strftime("%Y-%m-%d"))
    doc.add_paragraph('To: ' + end_date.strftime("%Y-%m-%d"))
    doc.add_paragraph('Utilization Mode: 24 hours')
    doc.add_paragraph('Schedule: UTILIZATION REPORTS')

    doc.add_paragraph(track_label)

    # create a table with 6 columns and 5 rows
    table = doc.add_table(rows=1, cols=9)
    table.style = 'Table Grid'

    # add headers to the table
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Date'
    hdr_cells[1].text = 'Distance'
    hdr_cells[2].text = 'Parked'
    hdr_cells[3].text = 'Parked Percent'
    hdr_cells[4].text = 'Driving'
    hdr_cells[5].text = 'Driving Percent'
    hdr_cells[6].text = 'Idling'
    hdr_cells[7].text = 'Idling Percent'
    hdr_cells[8].text = 'Total Hours'

    data = []

    for row_index in range(len(tracks)):
        row = tracks[row_index]

        raw_data = []        

        raw_data.append(row['time_start'][0:10])
        raw_data.append(row['distance'])

        if row["Parked"]:
            raw_data.append(row['duration'])
        else: 
            raw_data.append('00:00:00')

        if row["Parked"]:
            raw_data.append('00:00:00')
        else: 
            raw_data.append(row['duration'])

        if row["Idle_time"]:
            raw_data.append('00:00:00')
        else: 
            raw_data.append(row['duration'])

        raw_data.append(row['duration'])

        data.append(raw_data)

    delta = datetime.timedelta(days=1)

    results = {}

    data1 = []

    while start_date <= end_date:

        date_row = []
        parked_duration = "00:00:00"
        driving_duration = "00:00:00"
        idling_duration = "00:00:00"
        duration = 0
        for row in data:
            
            if start_date.strftime('%Y-%m-%d') == row[0]:
                duration += float(row[1])
                parked_duration = sum_times(parked_duration, row[2])
                driving_duration = sum_times(driving_duration, row[3])
                idling_duration = sum_times(idling_duration, row[4])
        
        driving_seconds = time.strptime(driving_duration, "%H:%M:%S")
        idling_seconds = time.strptime(idling_duration, "%H:%M:%S")

        driving_percent = datetime.timedelta(hours=driving_seconds.tm_hour,minutes=driving_seconds.tm_min,seconds=driving_seconds.tm_sec).total_seconds() / datetime.timedelta(hours=23,minutes=59,seconds=59).total_seconds() * 100
        idling_percent = datetime.timedelta(hours=idling_seconds.tm_hour,minutes=idling_seconds.tm_min,seconds=idling_seconds.tm_sec).total_seconds() / datetime.timedelta(hours=23,minutes=59,seconds=59).total_seconds() * 100
        date_row.append(round(driving_percent, 1))
        date_row.append(round(idling_percent, 1))
        results[start_date] = date_row

        data1_row = []
        data1_row.append(start_date.strftime('%Y-%m-%d'))
        data1_row.append(str(round(duration, 1)))
        if duration == 0:
            data1_row.append("23:59:59")
            parked_percent = 100
        else:
            parked_duration = sub_times("23:59:59", driving_duration)
            data1_row.append(parked_duration)
            parked_seconds = time.strptime(parked_duration, "%H:%M:%S")
            parked_percent = datetime.timedelta(hours=parked_seconds.tm_hour,minutes=parked_seconds.tm_min,seconds=parked_seconds.tm_sec).total_seconds() / datetime.timedelta(hours=23,minutes=59,seconds=59).total_seconds() * 100

        data1_row.append(round(parked_percent, 1))
        data1_row.append(driving_duration)
        data1_row.append(round(driving_percent, 1))
        data1_row.append(idling_duration)
        data1_row.append(round(idling_percent, 1))
        data1_row.append("23:59:59")
        
        data1.append(data1_row)

        start_date += delta

    for row in data1:
        row_cells = table.add_row().cells
        row_cells[0].text = row[0]
        row_cells[1].text = str(row[1])
        row_cells[2].text = row[2]
        row_cells[3].text = str(row[3])
        row_cells[4].text = row[4]
        row_cells[5].text = str(row[5])
        row_cells[6].text = row[6]
        row_cells[7].text = str(row[7])
        row_cells[8].text = row[8]

    # create a bar chart
    category_names = ['Driving', 'Idling']

    labels = list(results.keys())
    data = np.array(list(results.values()))
    data_cum = data.cumsum(axis=1)
    category_colors = plt.get_cmap('RdYlGn')(
        np.linspace(0.15, 0.85, data.shape[1]))

    fig, ax = plt.subplots(figsize=(7.2, 5))
    ax.invert_yaxis()
    ax.xaxis.set_visible(True)
    ax.set_xlim(0, np.sum(data, axis=1).max())

    for i, (colname, color) in enumerate(zip(category_names, category_colors)):
        widths = data[:, i]
        starts = data_cum[:, i] - widths
        ax.barh(labels, widths, left=starts, height=0.5,
                label=colname, color=color)
        xcenters = starts + widths / 2

        r, g, b, _ = color
        text_color = 'white' if r * g * b < 0.5 else 'darkgrey'
        for y, (x, c) in enumerate(zip(xcenters, widths)):
            ax.text(x, y, str(int(c)), ha='center', va='center',
                    color=text_color)
    ax.legend(ncol=len(category_names), bbox_to_anchor=(0, 1),
              loc='lower left', fontsize='small')

    fig.savefig('dates_vs_duration.png')

    # add the chart to the Word document
    doc.add_picture('dates_vs_duration.png')

    # save the Word document
    doc.save(save_file2) 

    return save_file2

def export_data3(tracks):
    # create a new Word document
    doc = docx.Document()

    # add a heading to the document
    doc.add_heading('Geofence visits', 0)

    doc.add_paragraph(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' - intervals:17')

    # create a table with 6 columns and 5 rows
    table = doc.add_table(rows=1, cols=6)
    table.style = 'Table Grid'

    # add headers to the table
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Geofence'
    hdr_cells[1].text = 'Entrance_Time'
    hdr_cells[2].text = 'Entrance_Place'
    hdr_cells[3].text = 'Exit_Time'
    hdr_cells[4].text = 'Exit_Place'
    hdr_cells[5].text = 'Duration'

    for row in tracks:
        row_cells = table.add_row().cells
        row_cells[0].text = row['track_label']
        row_cells[1].text = row['time_start']
        row_cells[2].text = row['from_address']
        row_cells[3].text = row['time_end']
        row_cells[4].text = row['to_address']
        row_cells[5].text = row['duration']

    doc.save(save_file3) 

    return save_file3

def sum_times(time1, time2):
    # Convert time strings to seconds
    time1_secs = sum(int(x) * 60 ** i for i, x in enumerate(reversed(time1.split(":"))))
    time2_secs = sum(int(x) * 60 ** i for i, x in enumerate(reversed(time2.split(":"))))
    
    # Calculate total seconds
    total_secs = time1_secs + time2_secs
    
    # Convert total seconds back to "hh:mm:ss" format
    hours, remainder = divmod(total_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def sub_times(time1, time2):
    # Convert time strings to seconds
    time1_secs = sum(int(x) * 60 ** i for i, x in enumerate(reversed(time1.split(":"))))
    time2_secs = sum(int(x) * 60 ** i for i, x in enumerate(reversed(time2.split(":"))))
    
    # Calculate total seconds
    sub_secs = time1_secs - time2_secs
    
    # Convert total seconds back to "hh:mm:ss" format
    hours, remainder = divmod(sub_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"