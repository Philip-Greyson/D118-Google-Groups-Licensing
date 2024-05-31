# # doStudentGroups.pyw

The script that handles adding our students to the correct individual building groups, as well as the overall student group and the graduation year groups.

## Overview

This script assigns students to building email groups based on what building they are enrolled in in PowerSchool, in a fashion that is very similar to how the staff group script functions.
It first connects to PowerSchool to get a list of all building codes that are not excluded from state reporting and their abbreviations. These abbreviations are used to construct the group email names, and it puts the school code and abbreviation pairings into a dictionary for later reference. It also finds the current year through the next 15 years to construct graduation class groups. Then it checks for the current members of each schools student group, as well as the grad years and the overall student group. Each member of a group and their role gets added to a dict, and each group dict is added to a master dict which can then be searched through to see if a specific user is a member of any of the groups. Essentially caching the group members at the beginning saves a lot of time in API calls to check individual group memberships for users later.
Then each user in the specified student Organizational Unit is processed, their home school is checked to make sure they are a member of that school's group and no other buildings. If they are in groups they don't belong in, their membership role is checked. If they are a normal member they are removed, but if they have an elevated role (manager or owner) they are not. This allows for them to be added to other groups they are not enrolled in if needed for some reason.

## Requirements

In addition to the Python Google API library as referenced in the main readme, this project has the following requirements:

**This script's main function relies on a few custom fields being populated with the student's home school and graduation year**. My PowerSchool to Google Admin student sync script handles that for us, you can find it [here](https://github.com/Philip-Greyson/D118-PS-Student-Sync). You must define `CUSTOM_ATTRIBUTE_SYNC_CATEGORY`, `CUSTOM_ATTRIBUTE_SCHOOL`, and `CUSTOM_ATTRIBUTE_GRAD_YEAR`,  to match the category and field names for this information.

The following Environment Variables must be set on the machine running the script:

- POWERSCHOOL_READ_USER
- POWERSCHOOL_DB_PASSWORD
- POWERSCHOOL_PROD_DB

These are fairly self explanatory, and just relate to the usernames, passwords, and host IP/URLs for PowerSchool. If you wish to directly edit the script and include these credentials or to use other environment variable names, you can.
There are additional Environment Variables that are used to define how the group names are constructed or the names of the overall district groups, these must either be set or the script be edited to include them directly.

- EMAIL_SUFFIX - The @domain.com part of the email
- STUDENT_SUFFIX - A word/suffix that will follow the school abbreviation for staff groups, before the main email suffix
- GRAD_YEAR_PREFIX - A word/prefix that will come before the actual year for the grad year groups
- STUDENT_OU - This assumes you have all students members inside a main "umbrella" Google OU
- ALL_STUDENT_GROUP - The email address for the district wide student group

Additionally, the following Python libraries must be installed on the host machine (links to the installation guide):

- [Python-oracledb](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html)

## Customization

- This script obviously makes a lot of assumptions on how your Google organization is set up, like needing to have all students under a main umbrella OU. If your organization structure is such that the students are underneath a building OU that also has staff in it, I would suggest just editing the script to call each staff OU individually, or it will add a lot of processing time going through the staff when not necessary. Just call the `process_groups()` function with each OU.
- If you would like to skip specific OUs inside of the OUs that are being called, you can edit the line `if ('test'  not  in ou.lower()) and ('fbla'  not  in ou.lower()) and ('pre students'  not  in ou.lower()):` to have strings that match words in the OUs you would like to skip. In our case, we skip any OUs that have the word "Test", "FBLA" or "PRE Students" in them.
- The email address for the student building groups are constructed from the abbreviation of the school, a suffix, and then the domain suffix. If you want to change how this is constructed, edit the `studentGroup = entry + studentSuffix + emailSuffix`  line found in the main function. The graduation groups are constructed from a prefix, the actual graduation year, and then the domain suffix. To change this, edit the `classGroup = gradYearPrefix +  str(year) + emailSuffix` line in the main function.
- The script will add users to the substitute teacher group if their staff type is 4 (which is PowerSchool's code for substitute) or if their homeschool matches a certain building. To change the building code for that, edit the `SUBSTITUTE_BUILDING_CODE` constant near the top of the script.
