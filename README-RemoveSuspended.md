# # removeSuspended.pyw

This script removes suspended accounts from any email groups they are members of.

## Overview

As a foreword: This script is very slow and inefficient. It looks through every suspended user and does a query for any groups they a member of, then removes them from the groups one at a time. It is much better to remove the users from groups immediately when they are suspended, which my PowerSchool to Google Admin scripts do, but this script can make sure none are missed by manual suspensions, users who were suspended previous to the automation, etc. I would only suggest running this once a week at most overnight as it can take many hours depending on domain size.

The script first does a query for all suspended users in Google Admin, then goes through the users one at a time, making sure they are actually suspended and then doing another query for all their groups they are a member of. If it finds groups, it removes the user from those groups one at a time, then moves on to the next user.

## Requirements

Besides the Python Google API library as referenced in the main readme, this project has no further requirements.

## Customization

This script is pretty simple, and there is no real customization intended as it is just going to remove all suspended users from all groups.
The only thing you might want to change would be to edit the overall query to limit it to specific OUs or other user properties.
