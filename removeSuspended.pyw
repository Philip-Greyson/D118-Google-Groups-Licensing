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

from datetime import *

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/admin.directory.group.member', 'https://www.googleapis.com/auth/apps.licensing']


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


# find suspended accounts, get all groups they are in, remove them from those groups
with open('suspendedUsersLog.txt', 'w') as log:
    startTime = datetime.now()
    startTime = startTime.strftime('%H:%M:%S')
    print(f'Execution started at {startTime}')
    print(f'Execution started at {startTime}', file=log)
    newToken =  ''
    while newToken is not None: # do a while loop while we still have the next page token to get more results with
        userResults = service.users().list(customer='my_customer', orderBy='email', pageToken=newToken, query="isSuspended=True").execute()
        newToken = userResults.get('nextPageToken')
        users = userResults.get('users', [])
        for user in users:
            try:
                email = user.get('primaryEmail') # .get allows us to retrieve the value of one of the sub results
                org = user.get('orgUnitPath')
                inactive = user.get('suspended')
                print(f'{email} - {org} - Suspended {inactive}')
                print(f'{email} - {org} - Suspended {inactive}', file=log)  

                if inactive == True:
                    userGroups = service.groups().list(userKey=email).execute().get('groups')
                    if userGroups:
                        for group in userGroups:
                            name = group.get('name')
                            groupEmail = group.get('email')
                            print(f'{email} is a member of: {name} - {groupEmail}')
                            print(f'{email} is a member of: {name} - {groupEmail}',file=log)
                            service.members().delete(groupKey=groupEmail, memberKey=email).execute()
                    else:
                        print('No groups')
                        print('No groups', file=log)
                else:
                    print('Not actually suspended!')
                    print('Not actually suspended!', file=log)
            except Exception as er:
                print(f'ERROR: {er}')
                print(f'ERROR: {er}',file=log)

    endTime = datetime.now()
    endTime = endTime.strftime('%H:%M:%S')
    print(f'Execution ended at {endTime}')
    print(f'Execution ended at {endTime}', file=log)

