"""Script to send data to SchooLinks from PowerSchool.

https://github.com/Philip-Greyson/D118-SchooLinks-PS-Sync
"""

# import modules
import datetime
import os
from datetime import *

import oracledb
import pysftp

DB_UN = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
DB_PW = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
DB_CS = os.environ.get('POWERSCHOOL_PROD_DB')  # the IP address, port, and database name to connect to

#set up sftp login info, stored as environment variables on system
SFTP_UN = os.environ.get('SCHOOLINKS_SFTP_USERNAME')
SFTP_PW = os.environ.get('SCHOOLINKS_SFTP_PASSWORD')
SFTP_HOST = os.environ.get('SCHOOLINKS_SFTP_ADDRESS')
CNOPTS = pysftp.CnOpts(knownhosts='known_hosts')  # connection options to use the known_hosts file for key validation

STUDENT_TAGS_ENABLED = False
STUDENT_TAGS_FILE_NAME = 'student_tags.csv'
GPA_ENABLED = False
GPA_FILE_NAME = 'gpa.csv'
ATTENDANCE_ENABLED = False
ATTENDANCE_FILE_NAME = 'attendance_percentage.csv'

print(f"Username: {DB_UN} | Password: {DB_PW} | Server: {DB_CS}")  # debug so we can see where oracle is trying to connect to/with
print(f"SFTP Username: {SFTP_UN} | SFTP Password: {SFTP_PW} | SFTP Server: {SFTP_HOST}")  # debug so we can see where pysftp is trying to connect to/with

if __name__ == '__main__':  # main file execution
    with open('schoolinks_log.txt', 'w') as log:  # open logging file
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)
        with oracledb.connect(user=DB_UN, password=DB_PW, dsn=DB_CS) as con:  # create the connecton to the database
            try:
                with con.cursor() as cur:  # start an entry cursor
                    print()
            except Exception as er:
                print(f'ERROR while doing initial PowerSchool query or file handling: {er}')
                print(f'ERROR while doing initial PowerSchool query or file handling: {er}', file=log)

        try:
            #after all the files are done writing and now closed, open an sftp connection to the server and place the file on there
            with pysftp.Connection(SFTP_HOST, username=SFTP_UN, password=SFTP_PW, cnopts=CNOPTS) as sftp:
                print(f'INFO: SFTP connection to SchooLinks at {SFTP_HOST} successfully established')
                print(f'INFO: SFTP connection to SchooLinks at {SFTP_HOST} successfully established', file=log)
                print(sftp.pwd)  # debug to list current working directory
                print(sftp.listdir())  # debug to list files and directory in current directory
                sftp.chdir('/automated')
                print(sftp.pwd)  # debug to list current working directory
                print(sftp.listdir())  # debug to list files and directory in current directory
                if STUDENT_TAGS_ENABLED:
                    sftp.put(STUDENT_TAGS_FILE_NAME)
                    print('INFO: Student tags placed on remote server')
                    print('INFO: Student tags placed on remote server', file=log)
                if GPA_ENABLED:
                    sftp.put(GPA_FILE_NAME)
                    print('INFO: GPA placed on remote server')
                    print('INFO: GPA placed on remote server', file=log)
                if ATTENDANCE_ENABLED:
                    sftp.put(ATTENDANCE_FILE_NAME)
                    print('INFO: Attendance placed on remote server')
                    print('INFO: Attendance placed on remote server', file=log)
        except Exception as er:
            print(f'ERROR while connecting or uploading to SchooLinks SFTP server: {er}')
            print(f'ERROR while connecting or uploading to SchooLinks SFTP server: {er}', file=log)

        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)
