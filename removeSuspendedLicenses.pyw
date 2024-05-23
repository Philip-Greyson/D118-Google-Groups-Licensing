"""Script to remove Google licenses from suspended accounts.

https://github.com/Philip-Greyson/D118-Google-Groups-Licensing

This script finds all the members of a certain Google SKU and product IDs.
If there are members who are suspended, the license is removed from their account.

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
licenseService = build('licensing', 'v1', credentials=creds)


productId = '101031'  # https://developers.google.com/admin-sdk/licensing/v1/how-tos/products
skus = ['1010310006', '1010310005']  # 1010310006 is teacher, 1010310005 is student
customer = 'd118.org'

# get a list of all license assignments for given product and sku, go through each user with that license and check if they are suspended, if so remove the license
def remove_licenses(product: str, sku: str) -> None:
        """Function to find all users of a certain productID and SKU and remove it from any suspended accounts using it."""
        newToken =  ''
        while newToken is not None:  # do a while loop while we still have the next page token to get more results with
            licenseResults = licenseService.licenseAssignments().listForProductAndSku(productId=product, skuId=sku, customerId= customer, pageToken=newToken).execute()  # get the licenses for the specified product and sku IDs
            newToken = licenseResults.get('nextPageToken')
            # print(licenseResults)
            userLicenses = licenseResults.get('items', [])  # get the actual license assignments block out of the overall results
            for user in userLicenses:  # go through each user in the license assignments
                try:
                    email = user.get('userId')  # get the email from result
                    userResults = service.users().get(userKey=email).execute()  # do a query for their email to get their Google profile info
                    if userResults.get('suspended'):  # if the suspended flag is true on their account, they should have a license removed
                        print(f'INFO: {email} is suspended and should not have a license, removing!')
                        print(f'INFO: {email} is suspended and should not have a license, removing!', file=log)
                        result = licenseService.licenseAssignments().delete(productId=product, skuId=sku, userId=email).execute()  # does the actual removal of the license
                        print(f'DBUG: {result}')  # debug
                    else:  # debug
                        print(f'INFO: {email} is enabled, no changes needed')
                        print(f'INFO: {email} is enabled, no changes needed', file=log)
                except Exception as er:
                    print(f'ERROR on {user}: {er}')
                    print(f'ERROR on {user}: {er}', file=log)


if __name__ == '__main__':  # main file execution
    with open('suspendedLicensesLog.txt', 'w') as log:
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'Execution started at {startTime}')
        print(f'Execution started at {startTime}', file=log)

        for entry in skus:
            remove_licenses(productId, entry)

        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'Execution ended at {endTime}')
        print(f'Execution ended at {endTime}', file=log)
