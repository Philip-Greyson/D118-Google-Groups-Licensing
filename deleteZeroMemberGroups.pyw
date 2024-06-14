"""Script to delete any google groups with no members left in them.

https://github.com/Philip-Greyson/D118-Google-Groups-Licensing

This script is designed to reduce the bloat of thousands of email groups by deleting any groups that have under a certain number of members in them.
It goes through each group in the domain one at a time, checking the member count, and attempting to delete them if they are under the specified value.

Needs the google-api-python-client, google-auth-httplib2 and the google-auth-oauthlib
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

import json
import os.path
from datetime import *
from typing import get_type_hints

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

# define the min number of users a group can have before being deleted. ANY GROUPS WITH LOWER THAN THIS NUMBER OF MEMBERS WILL BE CULLED
TARGET_MEMBER_COUNT = 2
DOMAIN = 'd118.org'

if __name__ == '__main__':  # main file execution
    with open('groupDeletionLog.txt', 'w') as log:
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)
        groupToken = ''
        while groupToken is not None:  # start a loop while there are more results to grab
            groupResults = service.groups().list(domain=DOMAIN, orderBy='email', pageToken=groupToken).execute()  # list all groups in the domain
            groupToken = groupResults.get('nextPageToken')  # get the next page token to use for the next query
            groups = groupResults.get('groups')  # store the groups item in a new variable
            for group in groups:
                try:
                    groupEmail = group.get('email')
                    memberCount = int(group.get('directMembersCount'))
                    # print(memberCount)
                    if memberCount < TARGET_MEMBER_COUNT:
                        print(f'DBUG: Group {groupEmail} has {memberCount} direct members and should probably be deleted')
                        print(f'DBUG: Group {groupEmail} has {memberCount} direct members and should probably be deleted', file=log)
                        # do a second check for members since there might be subgroup members
                        members = service.members().list(groupKey=groupEmail, includeDerivedMembership='True').execute().get('members')  # get a member list of the group
                        if members and len(members) > TARGET_MEMBER_COUNT:  # if there are results, its not actually a 0 member group. Sometimes this happens with subgroups
                            for user in members:
                                print(f'ERROR: found {user} in group {groupEmail}')
                                print(f'ERROR: found {user} in group {groupEmail}', file=log)
                        else:  # if there are no results, the group can be deleted
                            print(f'INFO: Deleting {groupEmail}')
                            print(f'INFO: Deleting {groupEmail}',file=log)
                            service.groups().delete(groupKey=groupEmail).execute()  # delete the group
                    else:
                        print(f'DBUG: Group {groupEmail} has {memberCount} members')
                        # print(f'DBUG: Group {groupEmail} has {memberCount} members', file=log)  # debug to show member counts for every group as its processed
                except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
                    status = er.status_code
                    details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
                    print(f'ERROR {status} from Google API while processing group {group["email"]}: {details["message"]}. Reason: {details["reason"]}')
                    print(f'ERROR {status} from Google API while processing group {group["email"]}: {details["message"]}. Reason: {details["reason"]}', file=log)
                except Exception as er:
                    print(f'ERROR while processing group {group["email"]}: {er}')
                    print(f'ERROR while processing group {group["email"]}: {er}', file=log)

        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)
