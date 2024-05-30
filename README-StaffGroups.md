# # doStaffGroups.pyw

The script that handles adding our staff members to the correct individual building groups, as well as the overall district staff or substitute group.

## Overview

This script assigns staff members to building email groups based on what buildings they are active in in PowerSchool. It first connects to PowerSchool to get a list of all building codes that are not excluded from state reporting and their abbreviations. These abbreviations are used to construct the group email names, one for all staff in that building and one just for teachers. It puts the school code and abbreviation pairings into a dictionary for later reference. Then it checks for the current members of the staff and teacher groups for each school. Each member of a group and their role gets added to a dict, and each group dict is added to a master dict which can then be searched through to see if a specific user is a member of any of the groups. Essentially caching the group members at the beginning saves a lot of time in API calls to check individual group memberships for users later.
Then each user in the specified staff Organizational Unit is processed, their access list is checked along with their staff type from the custom fields, and added to the correct overall district or sub group (mutually exclusive) as well as the building staff and teacher groups. If they are in groups they don't belong in, their membership role is checked. If they are a normal member they are removed, but if they have an elevated role (manager or owner) they are not. This allows for administration to be added as managers to other buildings they are not actually assigned to in PowerSchool. Any groups they should be added to is also taken care of.
After the normal staff are processed, the same thing happens with the substitute teacher Organizational Unit.

## Requirements

In addition to the Python Google API library as referenced in the main readme, this project has the following requirements:

**This script's main function relies on a few custom fields being populated with the staff member's home school, staff type, and a semicolon delimited list of buildings they should have access to**. My PowerSchool to Google Admin staff sync script handles that, you can find it [here](https://github.com/Philip-Greyson/D118-PS-Staff-Sync). You must define `CUSTOM_ATTRIBUTE_SYNC_CATEGORY`, `CUSTOM_ATTRIBUTE_SCHOOL`, `CUSTOM_ATTRIBUTE_ACCESS_LIST`, `CUSTOM_ATTRIBUTE_TYPE` to match the category and field names for this information.

The following Environment Variables must be set on the machine running the script:

- POWERSCHOOL_READ_USER
- POWERSCHOOL_DB_PASSWORD
- POWERSCHOOL_PROD_DB

These are fairly self explanatory, and just relate to the usernames, passwords, and host IP/URLs for PowerSchool. If you wish to directly edit the script and include these credentials or to use other environment variable names, you can.
There are additional Environment Variables that are used to define how the group names are constructed or the names of the overall district groups, these must either be set or the script be edited to include them directly.

- EMAIL_SUFFIX - The @domain.com part of the email
- STAFF_SUFFIX - A word/suffix that will follow the school abbreviation for staff groups, before the main email suffix
- TEACHER_SUFFIX - A word/suffix that will follow the school abbreviation for teacher groups, before the main email suffix
- STAFF_OU - This assumes you have all staff members inside a main "umbrella" Google OU
- SUB_OU - This assumes you have all substitutes inside a main "umbrella" Google OU
- ALL_DISTRICT_GROUP - The email address for the district wide staff group
- SUBSTITUTE_GROUP - The email address for the district wide substitute teacher group

Additionally, the following Python libraries must be installed on the host machine (links to the installation guide):

- [Python-oracledb](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html)

## Customization

- This script obviously makes a lot of assumptions on how your Google organization is set up, from needed to have all staff and substitutes under separate main umbrella OUs. If your organization structure is such that the staff are underneath a building OU that also has students in it, I would suggest just editing the script to call each staff OU individually, or it will add a lot of processing time going through the students when not necessary. Just call the `process_groups()` function with each OU.
- The script assumes you have a different staff group from the teacher group at each building. This would be very difficult to change as it does all the checks in process_groups() assuming these two groups, but it would be possible if you took some time.
- The email address for the staff and teacher groups are constructed from the abbreviation of the school, a suffix, and then the domain suffix. If you want to change how this is constructed, edit the `staffGroup = entry + staffSuffix + emailSuffix` and `teacherGroup = entry + teacherSuffix + emailSuffix` lines found in the main function.
- The script will add users to the substitute teacher group if their staff type is 4 (which is PowerSchool's code for substitute) or if their homeschool matches a certain building. To change the building code for that, edit the `SUBSTITUTE_BUILDING_CODE` constant near the top of the script.
