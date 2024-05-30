# # D118-Google-Groups-Licensing

A collection of scripts to handle our Google groups syncs, pruning, and licenses.
Each individual script has its own readme with additional specific information about it.

## Overview

This project is a collection of 6 separate scripts that help us manage our Google email groups for staff and students, adding them the correct buildings or graduation classes, as well as removing suspended users from groups and deleting any groups that have no members in them. Additionally, it has a script that removes licenses from suspended users.
As there are multiple scripts, each one has its own readme file with any specific information on that script. Covered below are the shared requirements for all of these scripts.

## Requirements

All of the scripts interact with Google Admin through the API, so all of them need the [Python-Google-API](https://github.com/googleapis/google-api-python-client#installation) library installed.

In addition, an OAuth credentials.json file must be in the same directory as the overall script. This is the credentials file you can download from the Google Cloud Developer Console under APIs & Services > Credentials > OAuth 2.0 Client IDs. Download the file and rename it to credentials.json. When the program runs for the first time, it will open a web browser and prompt you to sign into a Google account that has the permissions to disable, enable, deprovision, and move the devices. Based on this login it will generate a token.json file that is used for authorization. When the token expires it should auto-renew unless you end the authorization on the account or delete the credentials from the Google Cloud Developer Console. One credentials.json file can be shared across multiple similar scripts if desired.
There are full tutorials on getting these credentials from scratch available online. But as a quickstart, you will need to create a new project in the Google Cloud Developer Console, and follow [these](https://developers.google.com/workspace/guides/create-credentials#desktop-app) instructions to get the OAuth credentials, and then enable APIs in the project (the Admin SDK API is used in this project).

## Customization

Individual script customization is possible and discussed further in each script specific readme. Be warned however that the script sync scripts are very specific to our district and therefore were not made with a ton of easy customization in mind.
