# # middleGradeGroups.pyw

The script that handles adding our middle school students to the grade level specific building groups.

## Overview

In our district, the middle schools specifically use grade level groups in addition to the overall building groups and graduation year groups. This script assigns them to these grade level groups.
It first connects to PowerSchool to get a list of all building codes and abbreviations based on the list of building codes supplied. These abbreviations plus the grade levels supplied are used to construct the group email names, and it puts the school code and abbreviation pairings into a dictionary for later reference. A specific grade level Organization Unit name is constructed from the base Student OU plus the school abbreviation and grade level, then each student in that OU and the associated grade level email group are retrieved and placed into a dict.
This script assigns students to building email groups based on what building they are enrolled in in PowerSchool, in a fashion that is very similar to how the staff group script functions. Essentially caching the group and OU members at the beginning saves a lot of time in API calls to check individual group memberships for users later.
Then each grade level group is processed, first removing any members who don't belong because they are not a member of the matching grade level OU. It will only remove them if they are a normal member of the group, to allow any owners and managers to remain in the group even when they are not in the correct OU. After invalid members are removed, the grade level OU members are processed and added to the grade level group if they are not already a member.

## Requirements

In addition to the Python Google API library as referenced in the main readme, this project has the following requirements:

The following Environment Variables must be set on the machine running the script:

- POWERSCHOOL_READ_USER
- POWERSCHOOL_DB_PASSWORD
- POWERSCHOOL_PROD_DB

These are fairly self explanatory, and just relate to the usernames, passwords, and host IP/URLs for PowerSchool. If you wish to directly edit the script and include these credentials or to use other environment variable names, you can.
There are additional Environment Variables that are used to define how the group names are constructed or the names of the overall district groups, these must either be set or the script be edited to include them directly.

- GRADE_LEVEL_SUFFIX - The suffix that will follow the school abbreviation and grade level, should also include the @domain.com part of the email
- STUDENT_OU - This assumes you have all students members inside a main "umbrella" Google OU

Additionally, the following Python libraries must be installed on the host machine (links to the installation guide):

- [Python-oracledb](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html)

## Customization

This script more so than the others is extremely specific to our district's needs, so it is going to be a little difficult to adapt. That being said, here are some of the things you might want to change

- You will need to change the `SCHOOL_IDS` constant to match the school codes in your PowerSchool instance this script should run on. Similarly, you need to define the grade numbers as strings in the `GRADES` constant.
- This script obviously makes a lot of assumptions on how your Google organization is set up, like needing to have all students under a main umbrella OU, then broken out to buildings after. It then constructs the grade level OUs with `org = STUDENT_OU +  '/'  + entry.upper() +  ' Students/'  + grade +  'th'` to result in something like /*Student OU*/*Building* Students/6th. If your grade level sub OU naming scheme is different you will want to change this line to match.
- The email address for the grade level groups are constructed from the abbreviation of the school, the grade, and then the grade level suffix. If you want to change how this is constructed, edit the `gradelevelGroupEmail = entry +  '-'  + grade + GRADE_LEVEL_SUFFIX`  line found in the main function.
- The script will add users to the substitute teacher group if their staff type is 4 (which is PowerSchool's code for substitute) or if their homeschool matches a certain building. To change the building code for that, edit the `SUBSTITUTE_BUILDING_CODE` constant near the top of the script.
