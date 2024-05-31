# # deleteZeroMemberGroups.pyw

This script deletes email groups in the domain that have under a specified member count.

## Overview

Because many groups are created by users or other automation systems, Google Classroom, etc, the email groups list expands each year which makes it difficult to find any by simply browsing.
This script is meant to help solve that by deleting any groups that have under a certain member count. This pairs well with the remove suspended script that removes any suspended accounts from all groups, so that as students graduate and staff leaves their old groups are deleted.
It simply queries all the email groups in the specified domain, then goes through each one, finds the member count, and if it is less than the target member count, it deletes it.
This can be a somewhat lengthy process depending on how many groups are in your domain.

## Requirements

Besides the Python Google API library as referenced in the main readme, this project has no further requirements.

## Customization

This script is pretty simple, so there are only two constants you need to customize for your use:

- `TARGET_MEMBER_COUNT` is the minimum member count of groups that should stay. Any groups with a member count **lower** than this number will be deleted. So if you wanted to only delete groups with no members, you would want to set it to 1. We have it set to 2 so that zero or one member groups will be deleted as a group with one member is not much of a group.
- `DOMAIN` is just the string of your Google domain.
