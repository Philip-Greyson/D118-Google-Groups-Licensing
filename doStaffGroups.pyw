"""Script to manage the email groups our students are part of.

https://github.com/Philip-Greyson/D118-Google-Groups-Licensing

Makes sure every student is a member of the all student group, then adds each student to their respective building and grad year group.
It will also remove the student from the incorrect school and grad year group.
Very similar in general to the staff group script.

Needs the google-api-python-client, google-auth-httplib2 and the google-auth-oauthlib
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

also needs oracledb: pip install oracledb --upgrade
"""

import os  # needed for environement variable reading
import os.path
import sys  # needed for  non-scrolling display
from datetime import *
from typing import get_type_hints

# importing module
import oracledb  # needed for connection to PowerSchool server (ordcle database)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# setup db connection
DB_UN = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
DB_PW = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
DB_CS = os.environ.get('POWERSCHOOL_PROD_DB')  # the IP address, port, and database name to connect to
print(f"Database Username: {DB_UN} |Password: {DB_PW} |Server: {DB_CS}")  # debug so we can see where oracle is trying to connect to/with

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/admin.directory.group.member', 'https://www.googleapis.com/auth/apps.licensing']

emailSuffix = os.environ.get('EMAIL_SUFFIX')
staffSuffix = os.environ.get('STAFF_SUFFIX')
teacherSuffix = os.environ.get('TEACHER_SUFFIX')
staffOU = os.environ.get('STAFF_OU')
substituteOU = os.environ.get('SUB_OU')
allDistrictGroup = os.environ.get('ALL_DISTRICT_GROUP')
substituteGroup = os.environ.get('SUBSTITUTE_GROUP')

CUSTOM_ATTRIBUTE_SYNC_CATEGORY = 'Synchronization_Data'  # the category name that the custom attributes will be in
CUSTOM_ATTRIBUTE_SCHOOL = 'Homeschool_ID'  # the field name for the homeschool id custom attribute in the sync category
CUSTOM_ATTRIBUTE_ACCESS_LIST = 'School_Access_List'  # field name for the school access list custom attribute in the sync category
CUSTOM_ATTRIBUTE_TYPE = 'Staff_Type'  # field name for the staff type custom attribute in the sync category
SUBSTITUTE_BUILDING_CODE = '500'  # string format of the buidling code that substitutes are stored in. If there is not a specific building it can be set to a blank string

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
    """Takes a groups email, puts all members of the group and their role into a temp dict. Then adds the temp dict to the overall memberLists dict."""
    try:
        staffMemberToken = ''  # blank primer token for multi-page query results
        tempDict = {}  # create a temp dict that will hold the members and their roles
        print(f'INFO: Getting group members for {group_email}')  # debug
        while staffMemberToken is not None:  # while we still have results to process
            staffMemberResults = service.members().list(groupKey=group_email, pageToken=staffMemberToken, includeDerivedMembership='True').execute()  # get the members of the group by email
            staffMemberToken = staffMemberResults.get('nextPageToken')
            staffMembers = staffMemberResults.get('members', [])  # separate the actual members array from the rest of the result
            for member in staffMembers:  # go through each member and store their email and role in variables
                staffMemberEmail = member.get('email')
                staffMemberType = member.get('role')
                # print(f'{staffMemberEmail} is a {staffMemberType}')
                tempDict.update({staffMemberEmail : staffMemberType})  # add the email : role entry to the dict
        memberLists.update({group_email : tempDict})  # update the overall master member dict with with this group's email and member sub-dict
    except Exception as er:
        if ("notFound" in str(er)):
            print(f'ERROR: Group {group_email} not found')
            print(f'ERROR: Group {group_email} not found',file=log)
        else:
            print(f'ERROR: {er}')
            print(f'ERROR: {er}',file=log)


# go through all staff members in the OU, look at their school access lists, and see if they are in the groups they belong in
def process_groups(org_unit: str) -> None:
    """Goes through all users in an OU, looks at the school access list and makes sure they are in the groups they belong in."""
    try:
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
                    email = user.get('primaryEmail')  # .get allows us to retrieve the value of one of the sub results
                    accessListTotal = str(user.get('customSchemas').get(CUSTOM_ATTRIBUTE_SYNC_CATEGORY).get(CUSTOM_ATTRIBUTE_ACCESS_LIST))  # get the school access list that is stored in the custom schema data
                    staffType = str(user.get('customSchemas').get(CUSTOM_ATTRIBUTE_SYNC_CATEGORY).get(CUSTOM_ATTRIBUTE_TYPE))  # get their staff type (teacher, staff, lunch, sub)
                    teacher = True if staffType == '1' else False  # flag for tracking whether a user is a teacher or not for teacher group purposes
                    # securityGroup = str(user.get('customSchemas').get('Synchronization_Data').get('Staff_Group'))  # get the security group number from custom schema field
                    homeschool = str(user.get('customSchemas').get(CUSTOM_ATTRIBUTE_SYNC_CATEGORY).get(CUSTOM_ATTRIBUTE_SCHOOL))  # get their homeschool ID
                    accessList = accessListTotal.split(';')  # split the access list by semicolon since that is the delimeter between entries
                    print(f'DBUG: {email} should have access to: {accessList}, teacher flag = {teacher}')  # debug
                    print(f'DBUG: {email} should have access to: {accessList}, teacher flag = {teacher}', file=log)  # debug

                    addBodyDict = {'email' : email, 'role' : 'MEMBER'}  # define a dict for the member email and role type, which is this case is just their email and the normal member role

                    # all normal staff should be in the all district group, where all subs should be in the all subs group and they should be mutually exclusive
                    ####### SUBSTITUTES PROCESSING FOR SUBSTITUTES GROUP
                    if (staffType == 4) or (homeschool == SUBSTITUTE_BUILDING_CODE):  # 4 is the sub type in PS, 500 is our sub building
                        # check for membership to substitute group
                        print(f'DBUG: User {email} should be in {substituteGroup} and not {allDistrictGroup}')
                        if memberLists.get(allDistrictGroup).get(email):  # check and see if they are a part of the all district group, if so we want to remove them
                            if memberLists.get(allDistrictGroup).get(email) == 'MEMBER':  # check and see if they are just a member, if so remove them, otherwise we do not want to touch the managers and owners
                                print(f'INFO: {email} currently a part of {allDistrictGroup}, will be removed')
                                print(f'INFO: {email} currently a part of {allDistrictGroup}, will be removed', file=log)
                                service.members().delete(groupKey=allDistrictGroup, memberKey=email).execute()  # do the removal from the group
                            else:
                                print(f'WARN: {email} is an elevated role in {allDistrictGroup} and will NOT be removed')
                                print(f'WARN: {email} is an elevated role in {allDistrictGroup} and will NOT be removed', file=log)
                        if not memberLists.get(substituteGroup).get(email):  # check and see if they are missing from the sub group, if so we want to add them
                            print(f'INFO: {email} currently not a member of {substituteGroup}, will be added')
                            print(f'INFO: {email} currently not a member of {substituteGroup}, will be added', file=log)
                            service.members().insert(groupKey=substituteGroup, body=addBodyDict).execute()  # do the addition to the group
                    ####### NORMAL STAFF PROCESSING FOR DISTRICT WIDE GROUP
                    else:  # if they are not a sub
                        # check for membership to the district wide group
                        print(f'DBUG: User should be in {allDistrictGroup} and not {substituteGroup}')
                        if memberLists.get(substituteGroup).get(email):  # check and see if they are a part of the sub group, if so we want to remove them
                            if memberLists.get(substituteGroup).get(email) == 'MEMBER':  # check and see if they are just a member, if so remove them, otherwise we do not want to touch the managers and owners
                                print(f'INFO: {email} currently a part of {substituteGroup}, will be removed')
                                print(f'INFO: {email} currently a part of {substituteGroup}, will be removed', file=log)
                                service.members().delete(groupKey=substituteGroup, memberKey=email).execute()  # do the removal from the group
                            else:
                                print(f'WARN: {email} is an elevated role in {substituteGroup} and will NOT be removed')
                                print(f'WARN: {email} is an elevated role in {substituteGroup} and will NOT be removed', file=log)
                        if not memberLists.get(allDistrictGroup).get(email):  # check and see if they are missing from the all district group, if so we want to add them
                            print(f'INFO: {email} currently not a member of {allDistrictGroup}, will be added')
                            print(f'INFO: {email} currently not a member of {allDistrictGroup}, will be added', file=log)
                            service.members().insert(groupKey=allDistrictGroup, body=addBodyDict).execute()  # do the addition to the group

                    # go through each school code : abbreviation pair to check membership for each building group
                    for schoolEntry in schoolAbbreviations.keys():
                        try:
                            staffGroupEmail = schoolAbbreviations.get(schoolEntry) + staffSuffix + emailSuffix
                            teacherGroupEmail = schoolAbbreviations.get(schoolEntry) + teacherSuffix + emailSuffix
                            if schoolEntry in accessList:  # if the school id number we are currently is in their access list, they should be a part of that school's groups
                                if teacher:
                                    print(f'DBUG: {email} should be in {staffGroupEmail} and {teacherGroupEmail}')  # debug
                                    # print(f'{email} should be in {staffGroupEmail} and {teacherGroupEmail}', file=log) # debug
                                    if not memberLists.get(teacherGroupEmail).get(email):  # check and see if they are in the member list for the teacher group already, if not we want to add them
                                        print(f'INFO: {email} currently not a member of {teacherGroupEmail}, will be added')
                                        print(f'INFO: {email} currently not a member of {teacherGroupEmail}, will be added', file=log)
                                        service.members().insert(groupKey=teacherGroupEmail, body=addBodyDict).execute()  # do the addition to the group
                                else:  # if they are not a teacher they should just be in the staff group
                                    print(f'DBUG: {email} should be in {staffGroupEmail}, but not {teacherGroupEmail}')  # debug
                                    # print(f'{email} should be in {staffGroupEmail}, but not {teacherGroupEmail}', file=log) # debug
                                    if memberLists.get(teacherGroupEmail).get(email):  # check and see if they are in the member list for teachers, if so we need to remove them
                                        if memberLists.get(teacherGroupEmail).get(email) == 'MEMBER':
                                            print(f'INFO: {email} is currently a part of {teacherGroupEmail}, will be removed')
                                            print(f'INFO: {email} is currently a part of {teacherGroupEmail}, will be removed', file=log)
                                            service.members().delete(groupKey=teacherGroupEmail, memberKey=email).execute()  # do the removal from the group
                                        else:
                                            print(f'WARN: {email} is an elevated role in {teacherGroupEmail} and will NOT be removed')
                                            print(f'WARN: {email} is an elevated role in {teacherGroupEmail} and will NOT be removed', file=log)
                                # do the staff group check for both teachers and non-teachers
                                if not memberLists.get(staffGroupEmail).get(email):  # check and see if they are in the member list already for the staff group, if not we want to add them
                                        print(f'INFO: {email} currently not a member of {staffGroupEmail}, will be added')
                                        print(f'INFO: {email} currently not a member of {staffGroupEmail}, will be added', file=log)
                                        service.members().insert(groupKey=staffGroupEmail, body=addBodyDict).execute()  # do the addition to the group
                            else:  # if they do not have the school number on their access list, they should not get access to the email groups
                                print(f'DBUG: {email} should NOT be in {staffGroupEmail} or {teacherGroupEmail}')  # debug
                                # check both groups for their membership. If they are members, check and see if they are only members or if they are owners/managers. If they are only members, we remove them
                                if memberLists.get(staffGroupEmail).get(email):  # check and see if they are a part of the staff group, if so we want to remove them
                                    if memberLists.get(staffGroupEmail).get(email) == 'MEMBER':  # check and see if they are just a member, if so remove them, otherwise we do not want to touch the managers and owners
                                        print(f'INFO: {email} currently a part of {staffGroupEmail}, will be removed')
                                        print(f'INFO: {email} currently a part of {staffGroupEmail}, will be removed', file=log)
                                        service.members().delete(groupKey=staffGroupEmail, memberKey=email).execute()  # do the removal from the group
                                    else:
                                        print(f'WARN: {email} is an elevated role in {staffGroupEmail} and will NOT be removed')
                                        print(f'WARN: {email} is an elevated role in {staffGroupEmail} and will NOT be removed', file=log)
                                # do the same thing but for the teacher group
                                if memberLists.get(teacherGroupEmail).get(email):  # check and see if they are a part of the teacher group, if so we want to remove them
                                    if memberLists.get(teacherGroupEmail).get(email) == 'MEMBER':  # check and see if they are just a member, if so remove them, otherwise we do not want to touch the managers and owners
                                        print(f'INFO: {email} currently a part of {teacherGroupEmail}, will be removed')
                                        print(f'INFO: {email} currently a part of {teacherGroupEmail}, will be removed', file=log)
                                        service.members().delete(groupKey=teacherGroupEmail, memberKey=email).execute()  # do the removal from the group
                                    else:
                                        print(f'WARN: {email} is an elevated role in {teacherGroupEmail} and will NOT be removed')
                                        print(f'WARN: {email} is an elevated role in {teacherGroupEmail} and will NOT be removed', file=log)
                        except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
                            status = er.status_code
                            details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
                            print(f'ERROR {status} from Google API while processing user {email} in building {schoolEntry}: {details["message"]}. Reason: {details["reason"]}')
                            print(f'ERROR {status} from Google API while processing user {email} in building {schoolEntry}: {details["message"]}. Reason: {details["reason"]}', file=log)
                        except Exception as er:
                            print(f'ERROR on user {email} for building {schoolEntry}, teacher {teacher}: {er}')
                            print(f'ERROR on user {email} for building {schoolEntry}, teacher {teacher}: {er}', file=log)
                except Exception as er:
                    print(f'ERROR on {user} - {er}')
                    print(f'ERROR on {user} - {er}',file=log)
    except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
        status = er.status_code
        details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
        print(f'ERROR {status} from Google API while getting users in OU {org_unit}: {details["message"]}. Reason: {details["reason"]}')
        print(f'ERROR {status} from Google API while getting users in OU {org_unit}: {details["message"]}. Reason: {details["reason"]}',file=log)
    except Exception as er:
        print(f'ERROR while performing query to get users in OU {org_unit}: {er}')
        print(f'ERROR while performing query to get users in OU {org_unit}: {er}')

if __name__ == '__main__':  # main file execution
    with oracledb.connect(user=DB_UN, password=DB_PW, dsn=DB_CS) as con:  # create the connecton to the database
        with con.cursor() as cur:  # start an entry cursor
            with open('StaffGroupsLog.txt', 'w') as log:
                startTime = datetime.now()
                startTime = startTime.strftime('%H:%M:%S')
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
                # schoolAbbreviations.update({'0': 'd118'} ) # add in another abbreviation for the district wide groups
                print(f'DBUG: School IDs and abbreviations: {schoolAbbreviations}')
                print(f'DBUG: School IDs and abbreviations: {schoolAbbreviations}', file=log)

                memberLists = {}  # make a master dict for group memberships, that will have sub-dict sof each member and their role as its values

                # find the members of each group once at the start so we do not have to constantly query via the api whether a user is a member, we can just do a list comparison
                for entry in schoolAbbreviations.values():
                    # go through each school abbreviation and find their staff group
                    staffGroup = entry + staffSuffix + emailSuffix
                    teacherGroup = entry + teacherSuffix + emailSuffix
                    get_group_members(staffGroup)
                    get_group_members(teacherGroup)
                    # print(staffGroup, file=log) # debug
                    # print(memberLists.get(staffGroup), file=log) # debug to see the actual member lists
                    # print(teacherGroup, file=log) # debug
                    # print(memberLists.get(teacherGroup), file=log) # debug to see the actual member lists
                get_group_members(allDistrictGroup)  # get membership for the district wide group added to dict
                get_group_members(substituteGroup)  # get membership for the district wide sub group added to dict

                print(f'DBUG: All groups members: {memberLists}')  # debug, now should have a dict containing each group email as the keys, and the value is a dict of its own containing the emails and roles of each member of the group
                # print((f'DBUG: All groups members: {memberLists}', file=log) # debug, now should have a dict containing each group email as the keys, and the value is a dict of its own containing the emails and roles of each member of the group

                process_groups(staffOU)  # process the staff groups for the main staff ou, this will also include any sub-ous
                process_groups(substituteOU)  # process the staff groups for the subs ou

                endTime = datetime.now()
                endTime = endTime.strftime('%H:%M:%S')
                print(f'INFO: Execution ended at {endTime}')
                print(f'INFO: Execution ended at {endTime}', file=log)
