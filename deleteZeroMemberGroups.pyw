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

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/admin.directory.group.member', 'https://www.googleapis.com/auth/admin.directory.orgunit', 'https://www.googleapis.com/auth/admin.directory.userschema', 'https://www.googleapis.com/auth/apps.licensing']

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

# find all groups in the domain, find ones that have 0 users, delete those groups
with open('groupDeletionLog.txt', 'w') as log:
    groupToken = ''
    while groupToken is not None:
        groupResults = service.groups().list(domain='d118.org', orderBy='email', pageToken=groupToken).execute()
        groupToken = groupResults.get('nextPageToken')
        groups = groupResults.get('groups')
        for group in groups:
            groupEmail = group.get('email')
            memberCount = group.get('directMembersCount')
            if memberCount == '0':
                print(f'Group {groupEmail} has no direct members and should probably be deleted')
                print(f'Group {groupEmail} has no direct members and should probably be deleted', file=log)
                # do a second check for members since there might be subgroup members
                members = service.members().list(groupKey=groupEmail, includeDerivedMembership='True').execute().get('members') # get a member list of the group
                if members: # if there are results, its not actually a 0 member group
                    for user in members:
                        print(f'ERROR: found {user} in group {groupEmail}')
                        print(f'ERROR: found {user} in group {groupEmail}', file=log)
                else: # if there are no results, the group has 0 members and can be deleted
                    print(f'Deleting {groupEmail}')
                    print(f'Deleting {groupEmail}',file=log)
                    service.groups().delete(groupKey=groupEmail).execute() # delete the group
            # else:
                # print(f'Group {groupEmail} has {memberCount} members')