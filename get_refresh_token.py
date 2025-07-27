import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# --- TEMPORARY FIX FOR LOCAL DEVELOPMENT (DO NOT USE IN PRODUCTION) ---
# This tells the oauthlib library to allow HTTP redirects for localhost.
# Remove this line for production, where HTTPS is mandatory.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# -----------------------------------------------------------------------

# --- IMPORTANT: UPDATE THIS PATH ---
# Replace with the actual absolute path to your client_secret JSON file.
CLIENT_SECRETS_FILE = 'path to the clinet.json file'  # <-- UPDATE THIS LINE

# These scopes MUST match exactly what you configured in the Google Cloud Console
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
# This REDIRECT_URI MUST match the "Authorized redirect URIs" in Google Cloud Console
REDIRECT_URI = 'http://localhost:8000/oauth2callback'

def get_credentials():
    credentials = None

    # Load existing token if available
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

    # If credentials are invalid or missing, start OAuth2 flow
    if not credentials or not credentials.valid or not credentials.refresh_token:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE,
                SCOPES,
                redirect_uri=REDIRECT_URI
            )

            # Generate the authorization URL
            authorization_url, state = flow.authorization_url(
                access_type='offline',        # To get a refresh token
                include_granted_scopes='true' # To include previously granted scopes
            )

            print("Please go to this URL and authorize access:")
            print(f"\n{authorization_url}\n")

            # Wait for user to paste the redirect URL from browser
            redirect_response = input("After authorizing in your browser, paste the FULL redirect URL here: ")

            # Fetch the token using the response
            flow.fetch_token(authorization_response=redirect_response)
            credentials = flow.credentials

        # Save the credentials for future use
        with open('token.pickle', 'wb') as token_file:
            pickle.dump(credentials, token_file)

    return credentials

if __name__ == '__main__':
    print("--- Starting Google OAuth Refresh Token Retrieval ---")
    creds = get_credentials()

    print("\n--- Credentials Obtained ---")
    print(f"Access Token: {creds.token}")
    print(f"Refresh Token: {creds.refresh_token}")  # This should now have a value
    print(f"Token Expiry: {creds.expiry}")

    print("\n======================================================================")
    print("IMPORTANT: Copy the Refresh Token, Client ID, and Client Secret below.")
    print("Add them to your .env file in the project root.")
    print("Example .env entries:")
    print(f"GOOGLE_CLIENT_ID='{creds.client_id}'")
    print(f"GOOGLE_CLIENT_SECRET='{creds.client_secret}'")
    print(f"GOOGLE_REFRESH_TOKEN='{creds.refresh_token}'")
    print("======================================================================")
