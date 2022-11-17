# Needs the google-api-python-client, google-auth-httplib2 and the google-auth-oauthlib
# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

from __future__ import print_function

import os.path

import json
from typing import get_type_hints

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# importing module
import oracledb # needed for connection to PowerSchool server (ordcle database)
import sys # needed for  non-scrolling display
import os # needed for environement variable reading
from datetime import *

# setup db connection
un = 'PSNavigator' #PSNavigator is read only, PS is read/write
pw = os.environ.get('POWERSCHOOL_DB_PASSWORD') #the password for the database account
cs = os.environ.get('POWERSCHOOL_PROD_DB') #the IP address, port, and database name to connect to
print("Username: " + str(un) + " |Password: " + str(pw) + " |Server: " + str(cs)) #debug so we can see where oracle is trying to connect to/with

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/admin.directory.group.member', 'https://www.googleapis.com/auth/apps.licensing']

emailSuffix = os.environ.get('EMAIL_SUFFIX')
staffSuffix = os.environ.get('STAFF_SUFFIX')
teacherSuffix = os.environ.get('TEACHER_SUFFIX')
staffOU = os.environ.get('STAFF_OU')
allDistrictGroup = os.environ.get('ALL_DISTRICT_GROUP')
substituteGroup = os.environ.get('SUBSTITUTE_GROUP')


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
def getGroupMembers(groupEmail):
    try:
        staffMemberToken = '' # blank primer token for multi-page query results
        tempDict = {} # create a temp dict that will hold the members and their roles
        print(groupEmail) # debug
        while staffMemberToken is not None: # while we still have results to process
            staffMemberResults = service.members().list(groupKey=groupEmail, pageToken=staffMemberToken, includeDerivedMembership='True').execute() # get the members of the group by email
            staffMemberToken = staffMemberResults.get('nextPageToken')
            staffMembers = staffMemberResults.get('members', []) # separate the actual members array from the rest of the result
            for member in staffMembers: # go through each member and store their email and role in variables
                staffMemberEmail = member.get('email')
                staffMemberType = member.get('role')
                # print(f'{staffMemberEmail} is a {staffMemberType}')
                tempDict.update({staffMemberEmail : staffMemberType}) # add the email : role entry to the dict
        memberLists.update({groupEmail : tempDict}) # update the overall master member dict with with this group's email and member sub-dict
    except Exception as er:
        if ("notFound" in str(er)):
            print(f'ERROR: Group {groupEmail} not found')
            print(f'ERROR: Group {groupEmail} not found',file=log)
        else:
            print(f'ERROR: {er}')
            print(f'ERROR: {er}',file=log)


# go through all staff members in the OU, look at their school access lists, and see if they are in the groups they belong in
def processGroups(orgUnit):
    userToken =  ''
    queryString = "orgUnitPath='" + orgUnit + "'" # have to have the orgUnit enclosed by its own set of quotes in order to work
    print(queryString)
    while userToken is not None: # do a while loop while we still have the next page token to get more results with
        userResults = service.users().list(customer='my_customer', orderBy='email', projection='full', pageToken=userToken, query=queryString).execute()
        userToken = userResults.get('nextPageToken')
        users = userResults.get('users', [])
        for user in users:
            # print(user) # debug
            try:
                email = user.get('primaryEmail') # .get allows us to retrieve the value of one of the sub results
                accessListTotal = str(user.get('customSchemas').get('Synchronization_Data').get('School_Access_List')) # get the school access list that is stored in the custom schema data
                staffType = str(user.get('customSchemas').get('Synchronization_Data').get('Staff_Type')) # get their staff type (teacher, staff, lunch, sub)
                teacher = True if staffType == '1' else False # flag for tracking whether a user is a teacher or not for teacher group purposes
                securityGroup = str(user.get('customSchemas').get('Synchronization_Data').get('Staff_Group'))
                homeschool = str(user.get('customSchemas').get('Synchronization_Data').get('Homeschool_ID')) # get their homeschool ID
                accessList = accessListTotal.split(';') # split the access list by semicolon since that is the delimeter between entries
                print(f'{email} should have access to: {accessList}') # debug
                print(f'{email} should have access to: {accessList}', file=log) # debug

                addBodyDict = {'email' : email, 'role' : 'MEMBER'} # define a dict for the member email and role type, which is this case is just their email and the normal member role

                # all normal staff should be in the all district group, where all subs should be in the all subs group and they should be mutually exclusive
                ####### SUBSTITUTES PROCESSING FOR SUBSTITUTES GROUP
                if (staffType == 4) or (homeschool == '500'): # 4 is the sub type in PS, 500 is our sub building
                    # check for membership to substitute group
                    print(f'User should be in {substituteGroup} and not {allDistrictGroup}')
                    if memberLists.get(allDistrictGroup).get(email): # check and see if they are a part of the all district group, if so we want to remove them
                        if memberLists.get(allDistrictGroup).get(email) == 'MEMBER': # check and see if they are just a member, if so remove them, otherwise we do not want to touch the managers and owners
                            print(f'ACTION: {email} currently a part of {allDistrictGroup}, will be removed')
                            print(f'ACTION: {email} currently a part of {allDistrictGroup}, will be removed', file=log)
                            service.members().delete(groupKey=allDistrictGroup, memberKey=email).execute() # do the removal from the group
                        else:
                            print(f'WARNING: {email} is an elevated role in {allDistrictGroup} and will NOT be removed')
                            print(f'WARNING: {email} is an elevated role in {allDistrictGroup} and will NOT be removed', file=log)
                    if not memberLists.get(substituteGroup).get(email): # check and see if they are missing from the sub group, if so we want to add them
                        print(f'ACTION: {email} currently not a member of {substituteGroup}, will be added')
                        print(f'ACTION: {email} currently not a member of {substituteGroup}, will be added', file=log)
                        service.members().insert(groupKey=substituteGroup, body=addBodyDict).execute() # do the addition to the group
                ####### NORMAL STAFF PROCESSING FOR DISTRICT WIDE GROUP
                else: # if they are not a sub
                    # check for membership to the district wide group
                    print(f'User should be in {allDistrictGroup} and not {substituteGroup}')
                    if memberLists.get(substituteGroup).get(email): # check and see if they are a part of the sub group, if so we want to remove them
                        if memberLists.get(substituteGroup).get(email) == 'MEMBER': # check and see if they are just a member, if so remove them, otherwise we do not want to touch the managers and owners
                            print(f'ACTION: {email} currently a part of {substituteGroup}, will be removed')
                            print(f'ACTION: {email} currently a part of {substituteGroup}, will be removed', file=log)
                            service.members().delete(groupKey=substituteGroup, memberKey=email).execute() # do the removal from the group
                        else:
                            print(f'WARNING: {email} is an elevated role in {substituteGroup} and will NOT be removed')
                            print(f'WARNING: {email} is an elevated role in {substituteGroup} and will NOT be removed', file=log)
                    if not memberLists.get(allDistrictGroup).get(email): # check and see if they are missing from the all district group, if so we want to add them
                        print(f'ACTION: {email} currently not a member of {allDistrictGroup}, will be added')
                        print(f'ACTION: {email} currently not a member of {allDistrictGroup}, will be added', file=log)
                        service.members().insert(groupKey=allDistrictGroup, body=addBodyDict).execute() # do the addition to the group

                # go through each school code : abbreviation pair to check membership for each building group
                for schoolEntry in schoolAbbreviations.keys():
                    try:
                        staffGroupEmail = schoolAbbreviations.get(schoolEntry) + staffSuffix + emailSuffix
                        teacherGroupEmail = schoolAbbreviations.get(schoolEntry) + teacherSuffix + emailSuffix
                        if schoolEntry in accessList: # if the school id number we are currently is in their access list, they should be a part of that school's groups
                            if teacher:
                                print(f'{email} should be in {staffGroupEmail} and {teacherGroupEmail}') # Debug
                                if not memberLists.get(teacherGroupEmail).get(email): # check and see if they are in the member list for the teacher group already, if not we want to add them
                                    print(f'ACTION: {email} currently not a member of {teacherGroupEmail}, will be added')
                                    print(f'ACTION: {email} currently not a member of {teacherGroupEmail}, will be added', file=log)
                                    service.members().insert(groupKey=teacherGroupEmail, body=addBodyDict).execute() # do the addition to the group
                            else: # if they are not a teacher they should just be in the staff group
                                print(f'{email} should be in {staffGroupEmail}') # debug
                            # do the staff group check for both teachers and non-teachers
                            if not memberLists.get(staffGroupEmail).get(email): # check and see if they are in the member list already for the staff group, if not we want to add them
                                    print(f'ACTION: {email} currently not a member of {staffGroupEmail}, will be added')
                                    print(f'ACTION: {email} currently not a member of {staffGroupEmail}, will be added', file=log)
                                    service.members().insert(groupKey=staffGroupEmail, body=addBodyDict).execute() # do the addition to the group
                        else: # if they do not have the school number on their access list, they should not get access to the email groups
                            print(f'{email} should NOT be in {staffGroupEmail} or {teacherGroupEmail}') # debug
                            # check both groups for their membership. If they are members, check and see if they are only members or if they are owners/managers. If they are only members, we remove them
                            if memberLists.get(staffGroupEmail).get(email): # check and see if they are a part of the staff group, if so we want to remove them
                                if memberLists.get(staffGroupEmail).get(email) == 'MEMBER': # check and see if they are just a member, if so remove them, otherwise we do not want to touch the managers and owners
                                    print(f'ACTION: {email} currently a part of {staffGroupEmail}, will be removed')
                                    print(f'ACTION: {email} currently a part of {staffGroupEmail}, will be removed', file=log)
                                    service.members().delete(groupKey=staffGroupEmail, memberKey=email).execute() # do the removal from the group
                                else:
                                    print(f'WARNING: {email} is an elevated role in {staffGroupEmail} and will NOT be removed')
                                    print(f'WARNING: {email} is an elevated role in {staffGroupEmail} and will NOT be removed', file=log)
                            # do the same thing but for the teacher group
                            if memberLists.get(teacherGroupEmail).get(email): # check and see if they are a part of the teacher group, if so we want to remove them
                                if memberLists.get(teacherGroupEmail).get(email) == 'MEMBER': # check and see if they are just a member, if so remove them, otherwise we do not want to touch the managers and owners
                                    print(f'ACTION: {email} currently a part of {teacherGroupEmail}, will be removed')
                                    print(f'ACTION: {email} currently a part of {teacherGroupEmail}, will be removed', file=log)
                                    service.members().delete(groupKey=teacherGroupEmail, memberKey=email).execute() # do the removal from the group
                                else:
                                    print(f'WARNING: {email} is an elevated role in {teacherGroupEmail} and will NOT be removed')
                                    print(f'WARNING: {email} is an elevated role in {teacherGroupEmail} and will NOT be removed', file=log)
                                
                    except Exception as er:
                        print(f'ERROR: in building {schoolEntry} on user {email}, teacher {teacher}: {er}')
                        print(f'ERROR: in building {schoolEntry} on user {email}, teacher {teacher}: {er}', file=log)
            except Exception as er:
                print(f'ERROR: on {user} - {er}')
                print(f'ERROR: on {user} - {er}',file=log)

# main program
with oracledb.connect(user=un, password=pw, dsn=cs) as con: # create the connecton to the database
    with con.cursor() as cur:  # start an entry cursor
        with open('StaffGroupsLog.txt', 'w') as log:
            startTime = datetime.now()
            startTime = startTime.strftime('%H:%M:%S')
            print(f'Execution started at {startTime}')
            print(f'Execution started at {startTime}', file=log)
            # Start by getting a list of schools id's and abbreviations for the "real" schools which are not excluded from state reporting
            cur.execute('SELECT abbreviation, school_number FROM schools WHERE State_ExcludeFromReporting = 0')
            schools = cur.fetchall()
            schoolAbbreviations = {} # define a dict to store the school codes and abbreviations linked
            for school in schools:
                # store results in variables mostly just for readability
                schoolAbbrev = school[0].lower() # convert to lower case since email groups are all lower
                schoolNum = str(school[1])
                # print(f'School {schoolAbbrev} - Code {schoolNum}')
                schoolAbbreviations.update({schoolNum : schoolAbbrev})
            # schoolAbbreviations.update({'0': 'd118'} ) # add in another abbreviation for the district wide groups
            print(schoolAbbreviations)
            print(schoolAbbreviations, file=log)

            memberLists = {} # make a master dict for group memberships, that will have sub-dict sof each member and their role as its values

            # find the members of each group once at the start so we do not have to constantly query via the api whether a user is a member, we can just do a list comparison
            for entry in schoolAbbreviations.values():
                # go through each school abbreviation and find their staff group
                staffGroup = entry + staffSuffix + emailSuffix
                teacherGroup = entry + teacherSuffix + emailSuffix
                getGroupMembers(staffGroup)
                getGroupMembers(teacherGroup)
            getGroupMembers(allDistrictGroup) # get membership for the district wide group added to dict
            getGroupMembers(substituteGroup) # get membership for the district wide sub group added to dict
                
            print(memberLists) # debug, now should have a dict containing each group email as the keys, and the value is a dict of its own containing the emails and roles of each member of the group
            
            processGroups(staffOU) # process the staff groups for the main staff ou, this will also include any sub-ous
            processGroups('/Substitute Teachers') # process the staff groups for the subs ou

            endTime = datetime.now()
            endTime = endTime.strftime('%H:%M:%S')
            print(f'Execution ended at {endTime}')
            print(f'Execution ended at {endTime}', file=log)