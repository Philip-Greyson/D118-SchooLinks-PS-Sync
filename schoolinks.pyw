"""Script to send data to SchooLinks from PowerSchool.

https://github.com/Philip-Greyson/D118-SchooLinks-PS-Sync

Does a query for enrolled students, finds their attendance, GPA, and tags and outputs to correct files which are uploaded to SchooLinks SFTP server.

needs oracledb: pip install oracledb --upgrade
needs pysftp: pip install pysftp --upgrade

See the following for PS table information:
https://ps.powerschool-docs.com/pssis-data-dictionary/latest/ps_adaadm_daily_ctod-ver5-0-0
https://ps.powerschool-docs.com/pssis-data-dictionary/latest/students-1-ver3-6-1
https://ps-compliance.powerschool-docs.com/pssis-il/latest/s_il_stu_x-ver-14-9-3
https://ps-compliance.powerschool-docs.com/pssis-il/latest/s_il_stu_plan504_x-ver-18-8-0
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

STUDENT_TAGS_ENABLED = True
STUDENT_TAGS_FILE_NAME = 'student_tags.csv'
GPA_ENABLED = True
GPA_FILE_NAME = 'gpa.csv'
ATTENDANCE_ENABLED = True
ATTENDANCE_FILE_NAME = 'attendance_percentage.csv'
IGNORED_SCHOOL_CODE = 901  # school code to ignore even if grades match high schoolers. We use this because we have a pre-enrolled building we want to ignore
SCHOOLINKS_SFTP_DIRECTORY = '/automated'

print(f"Username: {DB_UN} | Password: {DB_PW} | Server: {DB_CS}")  # debug so we can see where oracle is trying to connect to/with
print(f"SFTP Username: {SFTP_UN} | SFTP Password: {SFTP_PW} | SFTP Server: {SFTP_HOST}")  # debug so we can see where pysftp is trying to connect to/with

def debug_null_entries(id: int, fte: int, today: date) -> None:
    """Function to find and count the 'NULL' entries in the PS_Ada_ADM_Daily_Ctod table."""
    cur.execute('SELECT COUNT(CalendarDate) FROM PS_AdaAdm_Daily_Ctod WHERE CalendarDate <= :today AND AttendanceValue IS NULL AND studentid = :id AND FTEID = :fte', id = id, fte = fte, today = today)
    # cur.execute('SELECT COUNT(CalendarDate) FROM PS_AdaAdm_Daily_Ctod')
    null_count = cur.fetchall()[0][0]
    if null_count > 0:
        cur.execute('SELECT CalendarDate FROM PS_AdaAdm_Daily_Ctod WHERE CalendarDate <= :today AND AttendanceValue IS NULL AND studentid = :id AND FTEID = :fte', id = id, fte = fte, today = today)
        null_days = cur.fetchall()
        print(f'WARN: Student {stuNum} has {null_count} NULL entries in their AttendanceValue fields, total attendance may be inaccurate!')
        print(f'WARN: Student {stuNum} has {null_count} NULL entries in their AttendanceValue fields, total attendance may be inaccurate!', file=log)
        for day in null_days:
            print(day[0].strftime('%m/%d/%Y'))
            print(day[0].strftime('%m/%d/%Y'), file=log)


if __name__ == '__main__':  # main file execution
    with open('schoolinks_log.txt', 'w') as log:  # open logging file
        startTime = datetime.now()
        todaysDate = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)
        with open(ATTENDANCE_FILE_NAME, 'w') as attendance_output:  # open the attendance output file
            with open(GPA_FILE_NAME, 'w') as gpa_output:  # open the gpa output file
                with open(STUDENT_TAGS_FILE_NAME, 'w') as tags_output:  # open the tags output file
                    print('student_number,attendance_percentage', file=attendance_output)  # print out the header row to the attendance percentage file
                    print('student_number,numerator_unweighted,numerator_weighted', file=gpa_output)  # print out the header row to the gpa file
                    print('student_number,name,detailed_name,description', file=tags_output)  # print out the header row to the tags file
                    with oracledb.connect(user=DB_UN, password=DB_PW, dsn=DB_CS) as con:  # create the connecton to the database
                        try:
                            with con.cursor() as cur:  # start an entry cursor
                                cur.execute('SELECT students.student_number, students.id, students.fteid, u_def_ext_students0.simple_gpa, u_def_ext_students0.weighted_gpa,\
                                            s_il_stu_x.iep, s_il_stu_plan504_x.participant, s_il_stu_x.lep, s_il_stu_x.lii, s_stu_crdc_x.giftedtalentedprograms_yn\
                                            FROM students LEFT JOIN u_def_ext_students0 ON students.dcid = u_def_ext_students0.studentsdcid LEFT JOIN s_il_stu_x ON students.dcid = s_il_stu_x.studentsdcid\
                                            LEFT JOIN s_il_stu_plan504_x ON students.dcid = s_il_stu_plan504_x.studentsdcid LEFT JOIN s_stu_crdc_x ON students.dcid = s_stu_crdc_x.studentsdcid\
                                            WHERE students.enroll_status = 0 AND students.grade_level IN (8,9,10,11,12) AND NOT students.schoolid = :school ORDER BY students.student_number DESC', school = IGNORED_SCHOOL_CODE)
                                students = cur.fetchall()
                                for student in students:
                                    try:
                                        stuNum = str(int(student[0]))  # strip out the trailing .0 by converting to int then string
                                        stuID = int(student[1])
                                        stuFTE = int(student[2])
                                        simpleGPA = float(student[3]) if student[3] else None  # retrieve simple gpa from custom field if it exists, otherwise set to none
                                        weightedGPA = float(student[4]) if student[4] else None  # retrieve weighted gpa from custom field if it exists, otherwise set to none
                                        iep = True if student[5] == 1 else False
                                        section504 = True if student[6] == 1 else False
                                        ell = True if student[7] == 1 else False
                                        lowIncome = True if student[8] == 1 else False
                                        gifted = True if str(student[9]) == 'Y' else False
                                        print(f'INFO: Starting student {stuNum}')
                                        print(f'INFO: Starting student {stuNum}', file=log)
                                        if ATTENDANCE_ENABLED:
                                            try:
                                                # debug_null_entries(stuID, stuFTE, todaysDate)  # call the function to find and print out the entries that have "NULL" in their AttendanceValue field
                                                cur.execute('SELECT SUM(AttendanceValue) FROM PS_AdaAdm_Daily_Ctod WHERE CalendarDate <= :today AND FTEID = :fte AND studentid = :id', id = stuID, fte = stuFTE, today = todaysDate)
                                                presentCount = cur.fetchall()[0][0]
                                                cur.execute('SELECT SUM(MembershipValue) FROM PS_AdaAdm_Daily_Ctod WHERE CalendarDate <= :today AND FTEID = :fte AND studentid = :id', id = stuID, fte = stuFTE, today = todaysDate)
                                                totalEnrolled = cur.fetchall()[0][0]
                                                if presentCount and totalEnrolled:  # if we have values for both results (aka not None/Null entries), proceed to find the percentage present and output it
                                                    percentPresent = presentCount / totalEnrolled
                                                    # print(f'DBUG: Student {stuNum} - Days Present: {presentCount} | Total Days Enrolled: {totalEnrolled} | Percent Present: {percentPresent}')
                                                    # print(f'DBUG: Student {stuNum} - Days Present: {presentCount} | Total Days Enrolled: {totalEnrolled} | Percent Present: {percentPresent}', file=log)
                                                    print(f'{stuNum},{percentPresent}', file=attendance_output)  # output the student entry to the attendance output file
                                                else:
                                                    print(f'WARN: Student {stuNum} has all "NULL" entries for their AttendanceValue or MembershipValue fields in PS_AdaAdm_Daily_Ctod, they will be skipped')
                                                    print(f'WARN: Student {stuNum} has all "NULL" entries for their AttendanceValue or MembershipValue fields in PS_AdaAdm_Daily_Ctod, they will be skipped', file=log)
                                            except Exception as er:
                                                print(f'ERROR while processing attendance for {stuNum}: {er}')
                                                print(f'ERROR while processing attendance for {stuNum}: {er}', file=log)
                                        if GPA_ENABLED:
                                            try:
                                                # print(f'DBUG: Student {stuNum} - Simple: {simpleGPA} | Weighted: {weightedGPA}')  # debug
                                                # print(f'DBUG: Student {stuNum} - Simple: {simpleGPA} | Weighted: {weightedGPA}', file=log)  # debug
                                                if simpleGPA and weightedGPA:  # if both the simple and weigted gpa's exist, we can proceed with output
                                                    print(f'{stuNum},{simpleGPA},{weightedGPA}', file=gpa_output)  # output the student entry to the gpa output file
                                                else:
                                                    print(f'WARN: Student {stuNum} does not have GPA entries in their custom fields, they will be skipped')
                                                    print(f'WARN: Student {stuNum} does not have GPA entries in their custom fields, they will be skipped', file=log)
                                            except Exception as er:
                                                print(f'ERROR while processing GPA for student {stuNum}: {er}')
                                                print(f'ERROR while processing GPA for student {stuNum}: {er}', file=log)
                                        if STUDENT_TAGS_ENABLED:
                                            try:
                                                # print(f'DBUG: Student {stuNum} - IEP: {iep} | 504: {section504} | EL: {ell} | Low Income: {lowIncome} | Gifted: {gifted}')  # debug
                                                # print(f'DBUG: Student {stuNum} - IEP: {iep} | 504: {section504} | EL: {ell} | Low Income: {lowIncome} | Gifted: {gifted}', file=log)  # debug
                                                if iep:
                                                    print(f'{stuNum},IEP,Individualized Education Plan,Student with IDEA Services', file=tags_output)
                                                if section504:
                                                    print(f'{stuNum},504,Section 504,Student with 504 Accomodation', file=tags_output)
                                                if ell:
                                                    print(f'{stuNum},EL,English Learner,Low English Proficiency Learner', file=tags_output)
                                                if lowIncome:
                                                    print(f'{stuNum},LI,Low Income,Low Income/Economically Disadvantaged Family', file=tags_output)
                                                if gifted:
                                                    print(f'{stuNum},GFT,Gifted & Talented,Student in Gifted or Talented Program', file=tags_output)
                                            except Exception as er:
                                                print(f'ERROR while processing tags for student {stuNum}: {er}')
                                                print(f'ERROR while processing tags for student {stuNum}: {er}', file=log)
                                    except Exception as er:
                                        print(f'ERROR on {student[0]}: {er}')
                                        print(f'ERROR on {student[0]}: {er}', file=log)
                        except Exception as er:
                            print(f'ERROR while doing initial PowerSchool query or file handling: {er}')
                            print(f'ERROR while doing initial PowerSchool query or file handling: {er}', file=log)

        try:
            #after all the files are done writing and now closed, open an sftp connection to the server and place the file on there
            with pysftp.Connection(SFTP_HOST, username=SFTP_UN, password=SFTP_PW, cnopts=CNOPTS) as sftp:
                print(f'INFO: SFTP connection to SchooLinks at {SFTP_HOST} successfully established')
                print(f'INFO: SFTP connection to SchooLinks at {SFTP_HOST} successfully established', file=log)
                # print(sftp.pwd)  # debug to list current working directory
                # print(sftp.listdir())  # debug to list files and directory in current directory
                sftp.chdir(SCHOOLINKS_SFTP_DIRECTORY)
                # print(sftp.pwd)  # debug to list current working directory
                # print(sftp.listdir())  # debug to list files and directory in current directory
                if STUDENT_TAGS_ENABLED:
                    sftp.put(STUDENT_TAGS_FILE_NAME)
                    print('ACTION: Student tags placed on remote server')
                    print('ACTION: Student tags placed on remote server', file=log)
                if GPA_ENABLED:
                    sftp.put(GPA_FILE_NAME)
                    print('ACTION: GPA placed on remote server')
                    print('ACTION: GPA placed on remote server', file=log)
                if ATTENDANCE_ENABLED:
                    sftp.put(ATTENDANCE_FILE_NAME)
                    print('ACTION: Attendance placed on remote server')
                    print('ACTION: Attendance placed on remote server', file=log)
        except Exception as er:
            print(f'ERROR while connecting or uploading to SchooLinks SFTP server: {er}')
            print(f'ERROR while connecting or uploading to SchooLinks SFTP server: {er}', file=log)

        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)
