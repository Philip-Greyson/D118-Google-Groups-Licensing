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
licenseService = build('licensing', 'v1', credentials=creds)


PRODUCT_ID = '101031'  # https://developers.google.com/admin-sdk/licensing/v1/how-tos/products
SKUS = ['1010310006', '1010310005']  # 1010310006 is teacher, 1010310005 is student
CUSTOMER = 'd118.org'

# get a list of all license assignments for given product and sku, go through each user with that license and check if they are suspended, if so remove the license
def remove_licenses(product: str, sku: str) -> None:
    """Function to find all users of a certain productID and SKU and remove it from any suspended accounts using it."""
    try:
        newToken =  ''
        print(f'INFO: Starting product {product} and SKU {sku} to remove suspended users')
        print(f'INFO: Starting product {product} and SKU {sku} to remove suspended users', file=log)
        while newToken is not None:  # do a while loop while we still have the next page token to get more results with
            licenseResults = licenseService.licenseAssignments().listForProductAndSku(productId=product, skuId=sku, customerId= CUSTOMER, pageToken=newToken).execute()  # get the licenses for the specified product and sku IDs
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
                        print(f'DBUG: {email} is enabled, no changes needed')
                        print(f'DBUG: {email} is enabled, no changes needed', file=log)
                except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
                        status = er.status_code
                        details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
                        print(f'ERROR {status} on {user["userId"]} while trying to remove product {product} and SKU {sku}: {details["message"]}. Reason: {details["reason"]}')
                        print(f'ERROR {status} on {user["userId"]} while trying to remove product {product} and SKU {sku}: {details["message"]}. Reason: {details["reason"]}', file=log)
                except Exception as er:
                    print(f'ERROR on {user["userId"]} while trying to remove product {product} and SKU {sku}: {er}')
                    print(f'ERROR on {user["userID"]} while trying to remove product {product} and SKU {sku}: {er}', file=log)
    except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
        status = er.status_code
        details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
        print(f'ERROR {status} from Google API while getting users with product {product} and SKU {sku}: {details["message"]}. Reason: {details["reason"]}')
        print(f'ERROR {status} from Google API while getting users with product {product} and SKU {sku}: {details["message"]}. Reason: {details["reason"]}',file=log)
    except Exception as er:
        print(f'ERROR while performing query to get users with product {product} and SKU {sku}: {er}')
        print(f'ERROR while performing query to get users with product {product} and SKU {sku}: {er}')


if __name__ == '__main__':  # main file execution
    with open('suspendedLicensesLog.txt', 'w') as log:
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)

        for entry in SKUS:
            remove_licenses(PRODUCT_ID, entry)

        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)
