import requests

# Replace with your Xibo CMS details
CMS_BASE_URL = "https://ashtondn.signcdn.com/api"
CLIENT_ID = "6ef1a59ccd51437aa1a7bbfca144c381915e8c7b"
CLIENT_SECRET = "9931fcce8db0fc2380926940c0ca30a5920b1a8996aaf049c6fbebde7ac608b6be23ad3415835dc1430ef7c45aeda6a3d2ef9a911eed4be2936c53691177e968bf405a2f520d5386fd77520e641d5825c876b0685b673aba153f10a521be6fc44e60b21f6260eee969764799534b5147c5cc2301f0b69d357488a3ece4c49a"

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
        print("Access token obtained successfully:", access_token)
    else:
        print("Failed to obtain access token.")
        print("Status Code:", response.status_code)
        print("Response:", response.text)

except Exception as e:
    print("An error occurred:", str(e))
