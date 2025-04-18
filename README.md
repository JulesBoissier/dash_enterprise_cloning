# Use this tool to clone all Apps on a DE5 Server to Another

This tool:

Gets the name for each App on your DE server using GQL. Then for each App:
Gets the list of services.
Gets the list of Local Environment Variables.
Creates an App on the second DE server.
Adds the Appropriate Services and Virtual Environments.
Clones the original Apps repository locally.
Uses "de deploy" to push this repo to the newly created App.
You will need to add a .env file with the following format:

OLD_USERNAME=
OLD_PASSWORD=
OLD_DEURL=tam.plotly.host
NEW_USERNAME=
NEW_PASSWORD=
NEW_DEURL=tam1.plotly.host

Additionally, apps on the new server will currently be named {original_app_name}-copy.

If you'd like to not have "-copy" appended, please modify lines 158 and 176 appropriately.