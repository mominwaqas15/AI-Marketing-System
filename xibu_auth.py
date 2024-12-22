import requests

# Replace with your Xibo CMS details
CMS_BASE_URL = "https://ashtondn.signcdn.com/api"
CLIENT_ID = "e735e4f01742bd971bbaf721ca8481072076fc21"
CLIENT_SECRET = "ee0f3e4d56eae56b98a8c74f821f50a8573a6089a615ee59759005c2d44427f1b6b2e56b7a61eaacc998b8479fd323ceb1871daea11a16e38173d51b21b5e5d45588ef2846d4e180ec36f5f2ecad9e8c20466d6db95db171c7e8a7da22e375811321e5103d3c63afd6d8481ed33a712eb2c3d4aaf747b9149192c9bd8b94c7"

# Token endpoint
token_url = f"{CMS_BASE_URL}/authorize/access_token"

# Payload for token request
payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}

try:
    # Request a new token
    response = requests.post(token_url, data=payload)

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")
        print("Access token obtained successfully:\n\n", access_token, "\n\n")
    else:
        print("Failed to obtain access token.")
        print("Status Code:", response.status_code)
        print("Response:", response.text)

except Exception as e:
    print("An error occurred:", str(e))