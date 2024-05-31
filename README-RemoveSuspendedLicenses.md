# # removeSuspendedLicenses.pyw

This script removes the Google Enterprise Licenses from suspended accounts.

## Overview

This script removes the [Google Enterprise Licenses](https://developers.google.com/admin-sdk/licensing/v1/how-tos/products) from suspended accounts so that the licenses are not wasted on those who are not using them. This is important for us as we have a limited number of the licenses especially for staff, so we need to remove it from those who no longer need it.
The script goes through each specified SKU for the specified productID, and queries all users that have the specific license SKU assigned to them. It goes through each user, queries if they are suspended and if they are, removes the license from their account.

## Requirements

Besides the Python Google API library as referenced in the main readme, this project has no further requirements.

## Customization

This script is pretty simple, but there are a few things you will want or need to change for your use:

- The `CUSTOMER`  constant should be changed to your Google domain.
- The `PRODUCT_ID` constant should be changed to the product ID of the relevant license, see [here](https://developers.google.com/admin-sdk/licensing/v1/how-tos/products) for the list
- The `SKUS` constant should be changed to a list of SKUs, found inside the product ID above, that you wish to check on
- If you have multiple product IDs, you will need to edit the script to process them separately, as the script was not designed with that in mind.
