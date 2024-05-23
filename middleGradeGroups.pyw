"""Script to add students in the middle school level OUs to the proper grade level email groups.

https://github.com/Philip-Greyson/D118-Google-Groups-Licensing



Needs the google-api-python-client, google-auth-httplib2 and the google-auth-oauthlib
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

also needs oracledb: pip install oracledb --upgrade
"""

import json
import os  # needed for environement variable reading
import os.path
from datetime import *
from typing import get_type_hints

# importing module
import oracledb  # needed for connection to PowerSchool server (ordcle database)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# setup db connection
DB_UN = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
DB_PW = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
DB_CS = os.environ.get('POWERSCHOOL_PROD_DB')  # the IP address, port, and database name to connect to
print(f"Database Username: {DB_UN} |Password: {DB_PW} |Server: {DB_CS}")  # debug so we can see where oracle is trying to connect to/with

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/admin.directory.group.member', 'https://www.googleapis.com/auth/apps.licensing']

STUDENT_OU = os.environ.get('STUDENT_OU')  # string containing the main umbrella level student OU
GRADE_LEVEL_SUFFIX = os.environ.get('MS_GRADE_LEVEL_SUFFIX')  # the suffix for the grade specific email name. In our case 6,7,8 all have the same suffix
SCHOOL_IDS = [1003, 1004]  # the building codes in powerschool that are the middle school buildings
GRADES = ['6', '7', '8']  # the grade level numbers in string format


creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

service = build('admin', 'directory_v1', credentials=creds)


def get_group_members(group_email: str) -> None:
    """Function to take a group by email, and return all the members of the group as well as their role.

    Makes a dict with these pairings, then adds that dict as well as the group email to the overall memberLists dict
    """
    try:
        studentMemberToken = ''  # blank primer token for multi-page query results
        tempDict = {}  # create a temp dict that will hold the members and their roles
        print(f'INFO: Getting email group members of {group_email} and adding them to the member lists')  # debug
        print(f'INFO: Getting email group members of {group_email} and adding them to the member lists',file=log)  # debug
        while studentMemberToken is not None:  # while we still have results to process
            studentMemberResults = service.members().list(groupKey=group_email, pageToken=studentMemberToken, includeDerivedMembership='True').execute()  # get the members of the group by email
            studentMemberToken = studentMemberResults.get('nextPageToken')
            studentMembers = studentMemberResults.get('members', [])  # separate the actual members array from the rest of the result
            for member in studentMembers:  # go through each member and store their email and role in variables
                studentEmail = member.get('email')
                studentMemberType = member.get('role')
                # print(f'{staffMemberEmail} is a {staffMemberType}')
                tempDict.update({studentEmail : studentMemberType})  # add the email : role entry to the dict
        memberLists.update({group_email : tempDict})  # update the overall master member dict with with this group's email and member sub-dict
        print(f'DBUG: GROUP MEMBERS: {group_email}: {tempDict}',file=log)
    except Exception as er:
        if ("notFound" in str(er)):
            print(f'ERROR: Group {group_email} not found')
            print(f'ERROR: Group {group_email} not found',file=log)
        else:
            print(f'ERROR: {er}')
            print(f'ERROR: {er}',file=log)

def get_ou_members(org_unit :str) -> None:
    """Gets a list of emails of accounts inside a specified OU."""
    userToken =  ''
    tempList = []  # create a temporary list that wiill hold all the member emails
    queryString = "orgUnitPath='" + org_unit + "'"  # have to have the orgUnit enclosed by its own set of quotes in order to work
    print(f'INFO: Getting OU members of {org_unit} and adding them to the OU lists')  # debug
    print(f'INFO: Getting OU members of {org_unit} and adding them to the OU lists',file=log)  # debug
    while userToken is not None:  # do a while loop while we still have the next page token to get more results with
        userResults = userResults = service.users().list(customer='my_customer', orderBy='email', pageToken=userToken, query=queryString).execute()
        userToken = userResults.get('nextPageToken')
        users = userResults.get('users', [])
        for user in users:  # go through each user
            email = user.get('primaryEmail')
            tempList.append(email)  # add the email to the list
    ouLists.update({org_unit: tempList})  # update the ouLists dict with the group org unit and members sub-list
    print(f'DBUG: ORG MEMBERS: {org_unit}: {tempList}',file=log)

def process_groups(org_unit: str, group_email: str) -> None:
    """Go through all student members in a given OU, and add them to a given group email if they are not already a member."""
    userToken =  ''
    queryString = "orgUnitPath='" + org_unit + "'"  # have to have the orgUnit enclosed by its own set of quotes in order to work
    # print(queryString)
    # print(queryString, file=log)
    print(f'INFO: Checking students in {org_unit} and adding them to {group_email} if not already present')
    print(f'INFO: Checking students in {org_unit} and adding them to {group_email} if not already present', file=log)
    while userToken is not None:  # do a while loop while we still have the next page token to get more results with
        userResults = service.users().list(customer='my_customer', orderBy='email', pageToken=userToken, query=queryString).execute()
        userToken = userResults.get('nextPageToken')
        users = userResults.get('users', [])
        for user in users:
            try:
                studentEmail = user.get('primaryEmail')  # .get allows us to retrieve the value of one of the sub results
                # print(f'DBUG: {studentEmail} should be a part of {groupEmail}')
                # print(f'DBUG: {studentEmail} should be a part of {groupEmail}', file=log)
                if not memberLists.get(group_email).get(studentEmail):  # if we cant find the user email in the group, they need to be added
                    addBodyDict = {'email' : studentEmail, 'role' : 'MEMBER'}  # define a dict for the member email and role type, which is this case is just their email and the normal member role
                    print(f'ACTION: {studentEmail} is currently not a member of {group_email}, will be added')
                    print(f'ACTION: {studentEmail} is currently not a member of {group_email}, will be added', file=log)
                    service.members().insert(groupKey=group_email, body=addBodyDict).execute()  # do the addition to the group
                # else: # debug
                #     print(f'DBUG: {studentEmail} is already a part of {group_email}, no action needed')
                #     print(f'DBUG: {studentEmail} is already a part of {group_email}, no action needed', file=log)
            except Exception as er:
                print(f'ERROR: on {user}: {er}')
                print(f'ERROR: on {user}: {er}',file=log)

def remove_invalid(org_unit: str, group_email: str) -> None:
    """Goes through emails in a given group email that has been previously stored with get_group_members, and removes any emails belonging to users who are not in the given OU."""
    print(f'INFO: Checking current members of {group_email} and removing any who are not in the OU {org_unit}')
    print(f'INFO: Checking current members of {group_email} and removing any who are not in the OU {org_unit}', file=log)
    try:
        memberList = memberLists.get(group_email)
        for email in memberList.keys():  # go through each email (the key) in the member list for our current group
            try:
                if memberList.get(email) == 'MEMBER':  # only go through the members, as we want to leave any owners/managers there regardless of whether they belong
                    # print(email)
                    # print(email, file=log)
                    if not email in ouLists.get(org_unit):  # if the email is not in the ouList for the correct orgUnit, they should be removed
                        print(f'ACTION: {email} should not be a member of {group_email}, will be removed')
                        print(f'ACTION: {email} should not be a member of {group_email}, will be removed', file=log)
                        service.members().delete(groupKey=group_email, memberKey=email).execute()  # do the removal from the group
                    # print(user, file=log)
            except Exception as er:
                print(f'ERROR on user {email}: {er}')
                print(f'ERROR on user {email}: {er}', file=log)
    except Exception as er:
        print(f'ERROR: Cannot remove invalid users from {group_email}: {er}')
        print(f'ERROR: Cannot remove invalid users from {group_email}: {er}', file=log)

if __name__ == '__main__':  # main file execution
    with oracledb.connect(user=DB_UN, password=DB_PW, dsn=DB_CS) as con:  # create the connecton to the database
        with con.cursor() as cur:  # start an entry cursor
            with open('MSGradeGroupsLog.txt', 'w') as log:
                startTime = datetime.now()
                startTime = startTime.strftime('%H:%M:%S')
                currentYear = int(datetime.now().strftime('%Y'))  # get current year for calculations of grad year classes
                print(f'INFO: Execution started at {startTime}')
                print(f'INFO: Execution started at {startTime}', file=log)

                schoolAbbreviations = {}  # define a dict to store the school codes and abbreviations linked
                # Start by getting a list of schools id's and abbreviations for just the defined schools
                for schoolID in SCHOOL_IDS:
                    cur.execute('SELECT abbreviation, school_number FROM schools WHERE school_number = :school', school=schoolID)
                    schools = cur.fetchall()
                    for school in schools:
                        # store results in variables mostly just for readability
                        schoolAbbrev = school[0].lower()  # convert to lower case since email groups are all lower
                        schoolNum = str(school[1])
                        # print(f'School {schoolAbbrev} - Code {schoolNum}')
                        schoolAbbreviations.update({schoolNum : schoolAbbrev})
                print(f'DBUG: Schools numbers and their abbreviations: {schoolAbbreviations}')
                print(f'DBUG: Schools numbers and their abbreviations: {schoolAbbreviations}', file=log)

                memberLists = {}  # make a master dict for group memberships, that will have sub-dict sof each member and their role as its values
                ouLists = {}  # make a master dict for users who are a member of the specific middle school grade ous, that will have sub lists of each grade ou

                # find the members of each group once at the start so we do not have to constantly query via the api whether a user is a member, we can just do a list comparison
                for entry in schoolAbbreviations.values():
                    for grade in GRADES:
                        # go through each school abbreviation and find their student group
                        gradelevelGroupEmail = entry + '-' + grade + GRADE_LEVEL_SUFFIX  # construct the group email from the school abbreviation and grade
                        org = STUDENT_OU + '/' + entry.upper() + ' Students/' + grade + 'th'  # construct the corresponding OU from school abbreviation and grade

                        get_group_members(gradelevelGroupEmail)  # update the memberlists with the current members of this group
                        get_ou_members(org)  # update the oulists with the current members of this OU

                        remove_invalid(org, gradelevelGroupEmail)  # go through the current member list and remove any users who arent also in the correct OU
                        process_groups(org, gradelevelGroupEmail)  # go through the correct OU and add anyone not already in the group

                endTime = datetime.now()
                endTime = endTime.strftime('%H:%M:%S')
                print(f'INFO: Execution ended at {endTime}')
                print(f'INFO: Execution ended at {endTime}', file=log)
