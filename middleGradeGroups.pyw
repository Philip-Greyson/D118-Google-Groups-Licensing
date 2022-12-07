# Script to find the students in the relevant middle school grade level OUs and add them to the proper grade level email groups

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
import os # needed for environement variable reading
from datetime import *

# setup db connection
un = 'PSNavigator' #PSNavigator is read only, PS is read/write
pw = os.environ.get('POWERSCHOOL_DB_PASSWORD') #the password for the database account
cs = os.environ.get('POWERSCHOOL_PROD_DB') #the IP address, port, and database name to connect to
print("Username: " + str(un) + " |Password: " + str(pw) + " |Server: " + str(cs)) #debug so we can see where oracle is trying to connect to/with

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/admin.directory.group.member', 'https://www.googleapis.com/auth/apps.licensing']

studentOU = os.environ.get('STUDENT_OU')
gradeLevelSuffix = os.environ.get('MS_GRADE_LEVEL_SUFFIX')


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
        studentMemberToken = '' # blank primer token for multi-page query results
        tempDict = {} # create a temp dict that will hold the members and their roles
        print(f'----Getting members of {groupEmail}----') # debug
        print(f'----Getting members of {groupEmail}----',file=log) # debug
        while studentMemberToken is not None: # while we still have results to process
            studentMemberResults = service.members().list(groupKey=groupEmail, pageToken=studentMemberToken, includeDerivedMembership='True').execute() # get the members of the group by email
            studentMemberToken = studentMemberResults.get('nextPageToken')
            studentMembers = studentMemberResults.get('members', []) # separate the actual members array from the rest of the result
            for member in studentMembers: # go through each member and store their email and role in variables
                studentEmail = member.get('email')
                studentMemberType = member.get('role')
                # print(f'{staffMemberEmail} is a {staffMemberType}')
                tempDict.update({studentEmail : studentMemberType}) # add the email : role entry to the dict
        memberLists.update({groupEmail : tempDict}) # update the overall master member dict with with this group's email and member sub-dict
        print(f'INFO: GROUP MEMBERS: {groupEmail}: {tempDict}',file=log)
    except Exception as er:
        if ("notFound" in str(er)):
            print(f'ERROR: Group {groupEmail} not found')
            print(f'ERROR: Group {groupEmail} not found',file=log)
        else:
            print(f'ERROR: {er}')
            print(f'ERROR: {er}',file=log)

def getOUMembers(orgUnit):
    userToken =  ''
    tempList = [] # create a temporary list that wiill hold all the member emails
    queryString = "orgUnitPath='" + orgUnit + "'" # have to have the orgUnit enclosed by its own set of quotes in order to work
    print(f'----Getting members of {orgUnit}----') # debug
    print(f'----Getting members of {orgUnit}----',file=log) # debug
    while userToken is not None: # do a while loop while we still have the next page token to get more results with
        userResults = userResults = service.users().list(customer='my_customer', orderBy='email', pageToken=userToken, query=queryString).execute()
        userToken = userResults.get('nextPageToken')
        users = userResults.get('users', [])
        for user in users: # go through each user
            email = user.get('primaryEmail')
            tempList.append(email) # add the email to the list
    ouLists.update({orgUnit: tempList}) # update the ouLists dict with the group org unit and members sub-list
    print(f'INFO: ORG MEMBERS: {orgUnit}: {tempList}',file=log)

# go through all student members in the OU, look at their school access lists, and see if they are in the groups they belong in
def processGroups(orgUnit, groupEmail):
    userToken =  ''
    queryString = "orgUnitPath='" + orgUnit + "'" # have to have the orgUnit enclosed by its own set of quotes in order to work
    # print(queryString)
    # print(queryString, file=log)
    print(f'----Checking students in {orgUnit} and adding them to {groupEmail} if not already present----')
    print(f'----Checking students in {orgUnit} and adding them to {groupEmail} if not already present----', file=log)
    while userToken is not None: # do a while loop while we still have the next page token to get more results with
        userResults = service.users().list(customer='my_customer', orderBy='email', pageToken=userToken, query=queryString).execute()
        userToken = userResults.get('nextPageToken')
        users = userResults.get('users', [])
        for user in users:
            try:
                studentEmail = user.get('primaryEmail') # .get allows us to retrieve the value of one of the sub results
                addBodyDict = {'email' : studentEmail, 'role' : 'MEMBER'} # define a dict for the member email and role type, which is this case is just their email and the normal member role
                # print(f'{email} should be a part of {groupEmail}')
                # print(f'{email} should be a part of {groupEmail}', file=log)
                if not memberLists.get(groupEmail).get(studentEmail):
                    print(f'ACTION: {studentEmail} is currently not a member of {groupEmail}, will be added')
                    print(f'ACTION: {studentEmail} is currently not a member of {groupEmail}, will be added', file=log)
                    service.members().insert(groupKey=groupEmail, body=addBodyDict).execute() # do the addition to the group
                # else: # debug
                #     print(f'INFO: {studentEmail} is already a part of {groupEmail}, no action needed')
                #     print(f'INFO: {studentEmail} is already a part of {groupEmail}, no action needed', file=log)
            except Exception as er:
                print(f'ERROR: on {user} - {er}')
                print(f'ERROR: on {user} - {er}',file=log)
# go through the email group and check if each member is part of the corresponding ou, if not then remove them
def removeInvalid(orgUnit, groupEmail):
    print(f'----Checking current members of {groupEmail} and removing any who are invalid----')
    print(f'----Checking current members of {groupEmail} and removing any who are invalid----', file=log)
    memberList = memberLists.get(groupEmail)
    for email in memberList.keys(): # go through each email (the key) in the member list for our current group
        if memberList.get(email) == 'MEMBER': # only go through the members, as we want to leave any owners/managers there regardless of whether they belong
            # print(email)
            # print(email, file=log)
            if not email in ouLists.get(orgUnit): # if the email is not in the ouList for the correct orgUnit, they should be removed
                print(f'ACTION: {email} should not be a member of {groupEmail}, will be removed')
                print(f'ACTION: {email} should not be a member of {groupEmail}, will be removed', file=log)
                service.members().delete(groupKey=groupEmail, memberKey=email).execute() # do the removal from the group
            # print(user, file=log)

# main program
with oracledb.connect(user=un, password=pw, dsn=cs) as con: # create the connecton to the database
    with con.cursor() as cur:  # start an entry cursor
        with open('MSGradeGroupsLog.txt', 'w') as log:
            startTime = datetime.now()
            startTime = startTime.strftime('%H:%M:%S')
            currentYear = int(datetime.now().strftime('%Y')) # get current year for calculations of grad year classes
            print(f'Execution started at {startTime}')
            print(f'Execution started at {startTime}', file=log)
            # Start by getting a list of schools id's and abbreviations for just the middle schools
            cur.execute('SELECT abbreviation, school_number FROM schools WHERE school_number = 1003 OR school_number = 1004')
            schools = cur.fetchall()
            schoolAbbreviations = {} # define a dict to store the school codes and abbreviations linked
            for school in schools:
                # store results in variables mostly just for readability
                schoolAbbrev = school[0].lower() # convert to lower case since email groups are all lower
                schoolNum = str(school[1])
                # print(f'School {schoolAbbrev} - Code {schoolNum}')
                schoolAbbreviations.update({schoolNum : schoolAbbrev})
            print(f'Schools numbers and their abbreviations: {schoolAbbreviations}')
            print(f'Schools numbers and their abbreviations: {schoolAbbreviations}', file=log)

            memberLists = {} # make a master dict for group memberships, that will have sub-dict sof each member and their role as its values
            ouLists = {} # make a master dict for users who are a member of the specific middle school grade ous, that will have sub lists of each grade ou

            grades = ['6', '7', '8']

            # find the members of each group once at the start so we do not have to constantly query via the api whether a user is a member, we can just do a list comparison
            for entry in schoolAbbreviations.values():
                for grade in grades:
                    # go through each school abbreviation and find their student group
                    gradelevelGroupEmail = entry + '-' + grade + gradeLevelSuffix # construct the group email from the school abbreviation and grade
                    org = studentOU + '/' + entry.upper() + ' Students/' + grade + 'th' # construct the corresponding OU from school abbreviation and grade

                    getGroupMembers(gradelevelGroupEmail) # update the memberlists with the current members of this group
                    getOUMembers(org) # update the oulists with the current members of this OU

                    removeInvalid(org, gradelevelGroupEmail) # go through the current member list and remove any users who arent also in the correct OU
                    processGroups(org, gradelevelGroupEmail) # go through the correct OU and add anyone not already in the group
                
            endTime = datetime.now()
            endTime = endTime.strftime('%H:%M:%S')
            print(f'Execution ended at {endTime}')
            print(f'Execution ended at {endTime}', file=log)