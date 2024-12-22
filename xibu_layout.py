import requests

# Replace with your Xibo CMS details
CMS_BASE_URL = "https://ashtondn.signcdn.com/api"  # Base URL of your Xibo CMS
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJpbmZvQHhpYm9zaWduYWdlLmNvbSIsImF1ZCI6ImU3MzVlNGYwMTc0MmJkOTcxYmJhZjcyMWNhODQ4MTA3MjA3NmZjMjEiLCJqdGkiOiI1YWY4NmQwMGIwNmM1MGUxNjE3YjczMmZlMTJmMTg5NjYzMmRmMTUwZGQ3MWI3YmI3YTQ3OGVlMDNhNDkyODYyZDAwMDZlZTdhMzliZTBlOCIsImlhdCI6MTczNDg2NjAyOS41NTQwMTEsIm5iZiI6MTczNDg2NjAyOS41NTQwNjcsImV4cCI6MTczNDg2OTYyOS41NDY1MjIsInN1YiI6IjMiLCJzY29wZXMiOltdfQ.Ah9U-PbQg3cYJ6Slc_OhV3de_q1CxvDD6QJLAxhV06FTHF2sYxPht4487rb9lFM13yar0MmY3vZ-pS8dRZxLTakv_oaUvJcpSdxdTOqVZffnVzM2BE44GYGkZoTqQFs8ykFPmsgbN2CBFTAjUyMOQ2yNhRFs_DzUirVBqBIG-1Wofzx9vlNNdGZteuUagZs4m2wysQdKnx7BKZN0VjrQ05GUJu0gHehTWu_zqic9KzLcNfTI6Mq5T5HtiffitjHbYYMVPEDkuZKt7JvARS_S2oZgpAVpDpQpK98jMo9Ni3S4aoIkBZdAT4Kq9Bo08VdNDZYSRAcWp7HBesojcwLo1Q"

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
