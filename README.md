
# D118-SchooLinks-PS-Sync

Script to send attendance, GPA, and student tags data to SchooLinks via SFTP.

## Overview

The script is pretty straightforward, starting by opening the output files and writing the header row in each. Then a query is done for active 8-12th grade students in PowerSchool, grabbing all the information that is needed except attendance data. Each student is gone through one at a time, and each section is done for each student if it is enabled using the constants at the top of the program (see customization below).
In the attendance section, the PS_AdaAdm_Daily_Ctod reporting view is used to find the number of days they were in attendance as well as the total days they could have been present. These are used to generate the percentage they were present, which is written out to the attendance output file with the student number.
In the GPA section, the GPA values from the SQL query are simply output to the GPA output file with the student number.
In the student tags section, the state demographic fields are used to see if students match a number of "tags". For each one they do, their student number is output along with the tag name and description.
Then after all students are processed, a connection is made to the SchooLinks SFTP server and all sections that are active have their file uploaded to the correct directory.

## Requirements

The following Environment Variables must be set on the machine running the script:

- POWERSCHOOL_READ_USER
- POWERSCHOOL_DB_PASSWORD
- POWERSCHOOL_PROD_DB
- SCHOOLINKS_SFTP_USERNAME
- SCHOOLINKS_SFTP_PASSWORD
- SCHOOLINKS_SFTP_ADDRESS

These are fairly self explanatory, and just relate to the usernames, passwords, and host IP/URLs for PowerSchool and the SchooLinks SFTP server (provided by them). If you wish to directly edit the script and include these credentials, you can.

In order for the GPA section to work, you must have the weighted and simple GPAs stored in custom fields for the SQL query to grab. The easiest method to do this is to set up an AutoSend job inside of PowerSchool using Data Access Tags (DATs) which can generate the GPA and output it to a file. Then set up an AutoComm job to import the weighted and simple GPA values into custom fields in the student table. We use and the script assumes custom field names of weighted_gpa and simple_gpa, but you can change that if you wish.

Additionally, the following Python libraries must be installed on the host machine (links to the installation guide):

- [Python-oracledb](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html)
- [pysftp](https://pypi.org/project/pysftp/)

**As part of the pysftp connection to the output SFTP server, you must include the server host key in a file** with no extension named "known_hosts" in the same directory as the Python script. You can see [here](https://pysftp.readthedocs.io/en/release_0.2.9/cookbook.html#pysftp-cnopts) for details on how it is used, but the easiest way to include this I have found is to create an SSH connection from a linux machine using the login info and then find the key (the newest entry should be on the bottom) in ~/.ssh/known_hosts and copy and paste that into a new file named "known_hosts" in the script directory.

## Customization

While the data that SchooLinks requires should be standard, this script is very customized to our specific fields and tables within PowerSchool. Without customization the attendance section should work, but the GPA and Student Tags will likely not unless you use the same custom field names for GPA as described above, and also use the IL demographic tables. Things that you will likely want to customize:

- By default all 3 sections (Attendance, GPA, Student Tags) are enabled, you can edit the constants `xxxxxx_ENABLED = True` and change them to `False` to disable the section.
- The student tags pull from IL specific demographic tables, namely [s_il_stu_x](https://ps-compliance.powerschool-docs.com/pssis-il/latest/s_il_stu_x-ver-14-9-3) and [s_il_stu_plan504_x](https://ps-compliance.powerschool-docs.com/pssis-il/latest/s_il_stu_plan504_x-ver-18-8-0).  Unless you use these tables in your PowerSchool setup, you will want to change them and the field names in the main SQL student query to match the tables and fields you can find the IEP, 504, LEP, and LII information in.
- The custom fields for GPA come from the u_def_ext_students0 table which is a basic extension to the students table, and the fields for weighted and simple GPAs are weighted_gpa and simple_gpa respectively. If you want to use a different extension table or field names for your GPA storing, you will need to set up the AutoComm into those fields and edit the names in the main SQL student query.
- We include grades 8-12 in the file outputs, if you wish to change the grades, you will need to edit the portion of the main SQL student query that has `... IN (8,9,10,11,12)...` and change the numbers to whichever grades you want to include.

 Other more minor things you might want to customize:

- We have a school for pre-registered students who are active but should not be included in queries. You can edit the constant `IGNORED_SCHOOL_CODE` to be the school code of a school you would like to ignore, or edit the main SQL student query to delete the `AND NOT students.schoolid = :school` and `school = IGNORED_SCHOOL_CODE` parts in order to remove this functionality.
- The tag names, detailed names, and descriptions are all defined as they are printed to the output file. If you would like to change them, simply edit the print statement to be the desired tag name, detailed name, or description.
- You can change the output file names and upload directory with the `xxxx_FILE_NAME` constants and `SCHOOLINKS_SFTP_DIRECTORY` constants near the top of the file, though these are what SchooLinks expects and should only change if they change their format for SFTP synchronization.
