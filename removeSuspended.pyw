"""Script to remove any suspended accounts from groups.

https://github.com/Philip-Greyson/D118-Google-Groups-Licensing

NOTE:This script is slow and inefficient, I only recommend running it sparingly as it will take many hours to complete dependent on domain size.
NOTE:In general, it is better to remove users from groups immediately when they are suspended instead of scanning the entire domain.
This script looks for all accounts in a domain that are suspended, then checks if they are members of any groups.
If they are, it attempts to remove them from the group before continuing to the next account.

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
if __name__ == '__main__':  # main file execution
    with open('suspendedUsersLog.txt', 'w') as log:
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)
        try:
            newToken =  ''
            while newToken is not None:  # do a while loop while we still have the next page token to get more results with
                userResults = service.users().list(customer='my_customer', orderBy='email', pageToken=newToken, query="isSuspended=True").execute()
                newToken = userResults.get('nextPageToken')
                users = userResults.get('users', [])
                for user in users:
                    try:
                        email = user.get('primaryEmail')  # .get allows us to retrieve the value of one of the sub results
                        org = user.get('orgUnitPath')
                        inactive = user.get('suspended')
                        print(f'DBUG: {email} - {org} - Suspended {inactive}')
                        print(f'DBUG: {email} - {org} - Suspended {inactive}', file=log)

                        if inactive == True:
                            userGroups = service.groups().list(userKey=email).execute().get('groups')
                            if userGroups:
                                for group in userGroups:
                                    name = group.get('name')
                                    groupEmail = group.get('email')
                                    print(f'INFO: {email} is a member of: {name} - {groupEmail} and will be removed')
                                    print(f'INFO: {email} is a member of: {name} - {groupEmail} and will be removed',file=log)
                                    service.members().delete(groupKey=groupEmail, memberKey=email).execute()
                            else:
                                print('DBUG: No groups')
                                # print('DBUG: No groups', file=log)
                        else:
                            print('ERROR: Not actually suspended!')
                            print('ERROR: Not actually suspended!', file=log)
                    except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
                        status = er.status_code
                        details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
                        print(f'ERROR {status} from Google API while processing {email}: {details["message"]}. Reason: {details["reason"]}')
                        print(f'ERROR {status} from Google API while processing {email}: {details["message"]}. Reason: {details["reason"]}', file=log)
                    except Exception as er:
                        print(f'ERROR: {er}')
                        print(f'ERROR: {er}',file=log)
        except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
            status = er.status_code
            details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
            print(f'ERROR {status} from Google API while getting suspended users: {details["message"]}. Reason: {details["reason"]}')
            print(f'ERROR {status} from Google API while getting suspended users: {details["message"]}. Reason: {details["reason"]}',file=log)
        except Exception as er:
            print(f'ERROR while performing query to get suspended users: {er}')
            print(f'ERROR while performing query to get suspended users: {er}')

        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)
