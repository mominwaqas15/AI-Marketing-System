import requests

# Base URL for the Xibo API
BASE_URL = "https://ashtondn.signcdn.com/api"
# Replace with your API token
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJpbmZvQHhpYm9zaWduYWdlLmNvbSIsImF1ZCI6ImU3MzVlNGYwMTc0MmJkOTTKPACaTw2mRGRaZUAb9XfW8Q5fEkW1wmSiLCJqdGkiOiI1YWY4NmQwMGIwNmM1MGUxNjE3YjczMmZlMTTKPACaTw2mRGRaZUAb9XfW8Q5fEkW1wmS3OGVlMDNhNDkyODYyZDAwMDZlZTTKPACaTw2mRGRaZUAb9XfW8Q5fEkW1wmSyOS41NTTKPACaTw2mRGRaZUAb9XfW8Q5fEkW1wmSwNjcsImV4cCI6MTTKPACaTw2mRGRaZUAb9XfW8Q5fEkW1wmSiLCJzY29wZXMiOltdfQ.Ah9U-PbQg3cYJ6Slc_OhV3de_q1CxvDD6QJLAxhV06FTHF2sYxPht4487rb9lFM13yar0MmY3vZ-pS8dRZxLTakv_oaUvJcpSdxdTTKPACaTw2mRGRaZUAb9XfW8Q5fEkW1wmSgbN2CBFTAjUyMOQ2yNhRFs_DzUirVBqBIG-1Wofzx9vlNNdGZteuUagZs4m2wysQdKnx7BKZN0VjrQ05GUJu0gHehTWu_zqic9KzLcNfTTKPACaTw2mRGRaZUAb9XfW8Q5fEkW1wmSRS_S2oZgpAVpDpQpK98jMo9Ni3S4aoIkBZdAT4Kq9Bo08VdNDZYSRAcWp7HBesojcwLo1Q"

def assign_layout_to_display(display_id, layout_id):
    """
    Assign a layout to a specific display by setting it as the default layout.
    
    :param display_id: ID of the display to assign the layout
    :param layout_id: ID of the layout to assign
    :return: Response from the API
    """
    url = f"{BASE_URL}/display/defaultlayout/{display_id}"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "layoutId": layout_id
    }
    
    try:
        response = requests.put(url, headers=headers, data=data)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        print("Layout successfully assigned to display!")
        return response.json()  # If the API returns a JSON response
    except requests.exceptions.RequestException as e:
        print(f"Error assigning layout to display: {e}")
        return None

if __name__ == "__main__":
    # Example usage:
    display_id = 43  # Replace with the actual display ID
    layout_id = 101  # Replace with the actual layout ID

    response = assign_layout_to_display(display_id, layout_id)
    if response:
        print(response)
    else:
        print("Failed to assign layout.")
