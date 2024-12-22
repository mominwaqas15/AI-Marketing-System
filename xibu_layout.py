import requests

# Replace with your Xibo CMS details
CMS_BASE_URL = "https://ashtondn.signcdn.com/api"  # Base URL of your Xibo CMS
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJpbmZvQHhpYm9zaWduYWdlLmNvbSIsImF1ZCI6IjZlZjFhNTljY2Q1MTQzN2FhMWE3YmJmY2ExNDRjMzgxOTE1ZThjN2IiLCJqdGkiOiJmNzM4NjA1OWQ3YTRhOGRkM2E4MGQxNmY4YzI3M2RiMTEyNjhkOGFmMjU1OTE3MDM0NWQzNmNiYzAwNjEwYmEzMDE0MGY3YTIzNjYwOWZmOSIsImlhdCI6MTczNDgxNzIwOC43ODg0NjcsIm5iZiI6MTczNDgxNzIwOC43ODg1MTQsImV4cCI6MTczNDgyMDgwOC43NzkzMTYsInN1YiI6IjIiLCJzY29wZXMiOlsiYWxsIl19.gbWdeUfTzhR4VrzzioMf3IaLhmgD0q2FjZwS6QMSJDHp2eze0c-ooLFTja4QGj3qlPgafYnXSvWGwdHL0PAlEvQeJEZic9jHbeOcfLp1v7iICZz1id47TLJPliuFPBvXflyyCc-_cCuh_udIxB3TH2AVJYryUVXXASRRfJwEJGC5c372vl16caCICb6bQcGwuZaJYlCReD1uoPTNI_hdlLZCDqlZ5P0ew86FTWrHnxC9tm9ubdA4nyWRQLF4cxQEuLytBtbSXAY_4OEhmBigBQTHxI1MQPJFNSOrEDkeayTAYbJqQfN26b21r0sD7KDwFN5mFJoUUEyVVBZDZ0svXQ"

# API endpoint for adding a layout
layout_add_url = f"{CMS_BASE_URL}/layout"

# Headers for the request
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/x-www-form-urlencoded",  # Required for formData
}

# Payload for the layout creation
payload = {
    "name": "My New Layout",  # Layout name
    "description": "A sample layout created via API",  # Optional layout description
    "resolutionId": 1,  # Resolution ID (e.g., 1 for default 1920x1080)
    "returnDraft": "0",  # Use "0" for False and "1" for True
    "code": "throughAPI",  # Unique code for the layout
    "folderId": 1,  # Folder ID if assigning to a folder (optional)
}

try:
    # Make the POST request to add the layout
    response = requests.post(layout_add_url, data=payload, headers=headers)

    # Check the response
    if response.status_code == 201:
        print("Layout created successfully!")
        print("Response:", response.json())
    else:
        print("Failed to create layout.")
        print("Status Code:", response.status_code)
        print("Response:", response.text)

except Exception as e:
    print("An error occurred:", str(e))
