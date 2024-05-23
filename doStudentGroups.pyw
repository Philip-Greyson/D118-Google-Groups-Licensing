"""Script to manage the email groups our students are part of.

https://github.com/Philip-Greyson/D118-Google-Groups-Licensing

Goes through the student OU, makes sure every student account is a member of the all student group, then adds each student to their respective building and grad year group.
It will also remove the student from the incorrect school and grad year group.
Very similar in general to the staff group script.

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

emailSuffix = os.environ.get('EMAIL_SUFFIX')
studentSuffix = os.environ.get('STUDENT_SUFFIX')
allStudentGroup = os.environ.get('ALL_STUDENT_GROUP')
studentOU = os.environ.get('STUDENT_OU')
gradYearPrefix = os.environ.get('GRAD_YEAR_PREFIX')


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

# function to take a group by email, and return all the members of the group as well as their role. Makes a dict with these pairings, then adds that dict as well as the group email to the overall memberLists dict
def get_group_members(group_email: str) -> None:
    """Function to take a group by email, and return all the members of the group as well as their role.

    Makes a dict with these pairings, then adds that dict as well as the group email to the overall memberLists dict.
    """
    try:
        studentMemberToken = ''  # blank primer token for multi-page query results
        tempDict = {}  # create a temp dict that will hold the members and their roles
        print(f'Getting members of {group_email}')  # debug
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
    except Exception as er:
        if ("notFound" in str(er)):
            print(f'ERROR: Group {group_email} not found')
            print(f'ERROR: Group {group_email} not found',file=log)
        else:
            print(f'ERROR: {er}')
            print(f'ERROR: {er}',file=log)


def process_groups(org_unit: str) -> None:
    """Go through all members in the given OU, look at their school access lists, and see if they are in the groups they belong in."""
    userToken =  ''
    queryString = "orgUnitPath='" + org_unit + "'"  # have to have the orgUnit enclosed by its own set of quotes in order to work
    print(queryString)
    while userToken is not None:  # do a while loop while we still have the next page token to get more results with
        userResults = service.users().list(customer='my_customer', orderBy='email', projection='full', pageToken=userToken, query=queryString).execute()
        userToken = userResults.get('nextPageToken')
        users = userResults.get('users', [])
        for user in users:
            # print(user) # debug
            try:
                ou = user.get('orgUnitPath')
                if ('test' not in ou.lower()) and ('fbla' not in ou.lower()) and ('pre students' not in ou.lower()):  # ignore any accounts that are in an OU that contains the word test, fbla, pre students
                    email = user.get('primaryEmail')  # .get allows us to retrieve the value of one of the sub results
                    homeschool = str(user.get('customSchemas').get('Synchronization_Data').get('Homeschool_ID'))  # get their homeschool ID
                    gradYear = str(user.get('customSchemas').get('Synchronization_Data').get('Graduation_Year'))  # get their homeschool ID

                    print(f'DBUG: {email} should be a part of {allStudentGroup}, {schoolAbbreviations.get(homeschool) + studentSuffix + emailSuffix} and {gradYearPrefix + gradYear + emailSuffix}')
                    print(f'DBUG: {email} should be a part of {allStudentGroup}, {schoolAbbreviations.get(homeschool) + studentSuffix + emailSuffix} and {gradYearPrefix + gradYear + emailSuffix}', file=log)
                    addBodyDict = {'email' : email, 'role' : 'MEMBER'}  # define a dict for the member email and role type, which is this case is just their email and the normal member role

                    # Check to see if they are a member of the all student group, if not we need to add them
                    if not memberLists.get(allStudentGroup).get(email):
                        print(f'INFO: {email} is currently not a member of {allStudentGroup}, will be added')
                        print(f'INFO: {email} is currently not a member of {allStudentGroup}, will be added', file=log)
                        service.members().insert(groupKey=allStudentGroup, body=addBodyDict).execute()  # do the addition to the group
                    # else: # debug
                    #     print(f'INFO: {email} is already a part of {allStudentGroup}, no action needed')
                    #     print(f'INFO: {email} is already a part of {allStudentGroup}, no action needed', file=log)

                    # go through each school code : abbreviation pair to check membership for each building group
                    for schoolEntry in schoolAbbreviations.keys():
                        try:
                            schoolGroupEmail = schoolAbbreviations.get(schoolEntry) + studentSuffix + emailSuffix
                            if schoolEntry == homeschool:  # if the school id number we are currently is their school, they should be a part of that school's groups
                                if not memberLists.get(schoolGroupEmail).get(email):  # if they are not a member of the group
                                    print(f'INFO: {email} is currently not a member of {schoolGroupEmail}, will be added')
                                    print(f'INFO: {email} is currently not a member of {schoolGroupEmail}, will be added', file=log)
                                    service.members().insert(groupKey=schoolGroupEmail, body=addBodyDict).execute()  # do the addition to the group
                                # else: # debug
                                #     print(f'INFO: {email} is already a part of {schoolGroupEmail}, no action needed')
                                #     print(f'INFO: {email} is already a part of {schoolGroupEmail}, no action needed', file=log)
                            else:  # if the current school entry is not their school, we need to make sure they are NOT part of that schools groups and remove them if they are
                                if memberLists.get(schoolGroupEmail).get(email):  # if they are a member of the group
                                    if memberLists.get(schoolGroupEmail).get(email) == 'MEMBER':  # check and see if they are just a member, if so remove them, otherwise we do not want to touch the managers and owners
                                        print(f'INFO: {email} should not be a member of {schoolGroupEmail}, will be removed')
                                        print(f'INFO: {email} should not be a member of {schoolGroupEmail}, will be removed', file=log)
                                        service.members().delete(groupKey=schoolGroupEmail, memberKey=email).execute()  # do the removal from the group
                                    else:  # if they are an elevated member just give a warning
                                        print(f'WARN: {email} is an elevated role in {schoolGroupEmail} and will NOT be removed')
                                        print(f'WARN: {email} is an elevated role in {schoolGroupEmail} and will NOT be removed', file=log)

                        except Exception as er:
                            print(f'ERROR: in building {schoolEntry} on user {email}: {er}')
                            print(f'ERROR: in building {schoolEntry} on user {email}: {er}', file=log)

                    # go through each grad year group to check membership
                    for year in gradYears:
                        try:
                            gradYearEmail = gradYearPrefix + str(year) + emailSuffix
                            if str(year) == gradYear:  # if the year we are currently on is their grad year, they should be a part of the group
                                if not memberLists.get(gradYearEmail).get(email):
                                    print(f'INFO: {email} is currently not a member of {gradYearEmail}, will be added')
                                    print(f'INFO: {email} is currently not a member of {gradYearEmail}, will be added', file=log)
                                    service.members().insert(groupKey=gradYearEmail, body=addBodyDict).execute()  # do the addition to the group
                                # else: # debug
                                #     print(f'INFO: {email} is already a part of {gradYearEmail}, no action needed')
                                #     print(f'INFO: {email} is already a part of {gradYearEmail}, no action needed', file=log)
                            else:  # if the year is not their grad year, we need to make sure they are NOT a part of that group
                                if memberLists.get(gradYearEmail).get(email):
                                    if memberLists.get(gradYearEmail).get(email) == 'MEMBER':  # check and see if they are just a member, if so remove them, otherwise we do not want to touch the managers and owners
                                        print(f'INFO: {email} should not be a member of {gradYearEmail}, will be removed')
                                        print(f'INFO: {email} should not be a member of {gradYearEmail}, will be removed', file=log)
                                        service.members().delete(groupKey=gradYearEmail, memberKey=email).execute()  # do the removal from the group
                                    else:  # if they are an elevated member just give a warning
                                        print(f'WARN: {email} is an elevated role in {gradYearEmail} and will NOT be removed')
                                        print(f'WARN: {email} is an elevated role in {gradYearEmail} and will NOT be removed', file=log)
                        except Exception as er:
                            print(f'ERROR: in grad year entry {schoolEntry} on user {email}: {er}')
                            print(f'ERROR: in grad year entry {schoolEntry} on user {email}: {er}', file=log)
            except Exception as er:
                print(f'ERROR: on {user} - {er}')
                print(f'ERROR: on {user} - {er}',file=log)

# main program
with oracledb.connect(user=DB_UN, password=DB_PW, dsn=DB_CS) as con:  # create the connecton to the database
    with con.cursor() as cur:  # start an entry cursor
        with open('StudentGroupsLog.txt', 'w') as log:
            startTime = datetime.now()
            startTime = startTime.strftime('%H:%M:%S')
            currentYear = int(datetime.now().strftime('%Y'))  # get current year for calculations of grad year classes
            print(f'INFO: Execution started at {startTime}')
            print(f'INFO: Execution started at {startTime}', file=log)
            # Start by getting a list of schools id's and abbreviations for the "real" schools which are not excluded from state reporting
            cur.execute('SELECT abbreviation, school_number FROM schools WHERE State_ExcludeFromReporting = 0')
            schools = cur.fetchall()
            schoolAbbreviations = {}  # define a dict to store the school codes and abbreviations linked
            for school in schools:
                # store results in variables mostly just for readability
                schoolAbbrev = school[0].lower()  # convert to lower case since email groups are all lower
                schoolNum = str(school[1])
                # print(f'School {schoolAbbrev} - Code {schoolNum}')
                schoolAbbreviations.update({schoolNum : schoolAbbrev})
            print(f'DBUG: Schools numbers and their abbreviations: {schoolAbbreviations}')
            print(f'DBUG: Schools numbers and their abbreviations: {schoolAbbreviations}', file=log)

            memberLists = {}  # make a master dict for group memberships, that will have sub-dict sof each member and their role as its values
            gradYears = []  # make an array that will hold the next 14 years to have as reference for graduation years

            for i in range(17):
                gradYears.append(currentYear + (i-1))  # start with 0 (-1) from the current year and go through the next 15 years

            print(f'DBUG: The graduation years in range: {gradYears}')  # debug
            print(f'DBUG: The graduation years in range: {gradYears}', file=log)  # debug

            # find the members of each group once at the start so we do not have to constantly query via the api whether a user is a member, we can just do a list comparison
            for entry in schoolAbbreviations.values():
                # go through each school abbreviation and find their student group
                studentGroup = entry + studentSuffix + emailSuffix
                get_group_members(studentGroup)

            for year in gradYears:
                classGroup = gradYearPrefix + str(year) + emailSuffix
                get_group_members(classGroup)

            get_group_members(allStudentGroup)  # get membership for the district wide student group added to dict

            print(memberLists)  # debug, now should have a dict containing each group email as the keys, and the value is a dict of its own containing the emails and roles of each member of the group
            # print(memberLists, file=log) # debug, now should have a dict containing each group email as the keys, and the value is a dict of its own containing the emails and roles of each member of the group
            process_groups(studentOU)  # process the student groups for the main student OU, this will also include any sub-OUs

            endTime = datetime.now()
            endTime = endTime.strftime('%H:%M:%S')
            print(f'INFO: Execution ended at {endTime}')
            print(f'INFO: Execution ended at {endTime}', file=log)
