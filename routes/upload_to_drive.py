from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Security, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import uuid
import logging
from dotenv import load_dotenv
import tempfile
from typing import List, Dict, Any

# Load environment variables from .env file
load_dotenv()

# Configure logging for better error visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Drive Upload"])

# --- Authorization Setup (Matching your jd_routes.py) ---
# Assuming 'decode_access_token' utility is available in 'utils' module
# You need to ensure 'utils.py' is accessible and contains 'decode_access_token'
from utils import decode_access_token

# This defines a security scheme for Bearer tokens, consistent with your other routes
security = HTTPBearer()

# ✅ Google Drive Setup for OAuth 2.0 (for personal accounts)
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
# Note: 'drive.file' scope only allows access to files created by the app.
# For deleting arbitrary files (even if created by the app), 'drive' scope is safer.
# You might need to re-run get_refresh_token.py if you change scopes in Cloud Console.

CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
REFRESH_TOKEN = os.getenv('GOOGLE_REFRESH_TOKEN')
FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

if not CLIENT_ID:
    raise ValueError("Environment variable 'GOOGLE_CLIENT_ID' not set in .env or environment. Please set it after creating OAuth credentials.")
if not CLIENT_SECRET:
    raise ValueError("Environment variable 'GOOGLE_CLIENT_SECRET' not set in .env or environment. Please set it after creating OAuth credentials.")
if not REFRESH_TOKEN:
    raise ValueError("Environment variable 'GOOGLE_REFRESH_TOKEN' not set in .env or environment. Please run the 'get_refresh_token.py' script first.")
if not FOLDER_ID:
    raise ValueError("Environment variable 'GOOGLE_DRIVE_FOLDER_ID' not set in .env or environment. Please provide the ID of your target Google Drive folder.")

credentials = None
drive_service = None

def get_drive_credentials():
    global credentials, drive_service

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            logger.info("Google Drive access token refreshed successfully.")
            drive_service = build('drive', 'v3', credentials=credentials)
            return credentials
        except Exception as e:
            logger.error(f"Error refreshing Google Drive access token: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to refresh Google Drive access token: {e}")

    if not credentials:
        try:
            credentials = Credentials(
                token=None,
                refresh_token=REFRESH_TOKEN,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                scopes=SCOPES
            )
            credentials.refresh(Request())
            logger.info("Initial Google Drive credentials created and access token obtained.")
            drive_service = build('drive', 'v3', credentials=credentials)
            return credentials
        except Exception as e:
            logger.error(f"Failed to create initial Google Drive credentials or obtain access token: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to authenticate with Google Drive: {e}")

try:
    get_drive_credentials()
except HTTPException as e:
    logger.critical(f"Application startup failed due to Google Drive authentication error: {e.detail}")
    raise

def upload_file_to_drive(file_path: str, filename: str) -> str:
    get_drive_credentials()

    media = MediaFileUpload(file_path, resumable=True)
    file_metadata = {
        'name': filename,
        'parents': [FOLDER_ID]
    }
    try:
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        logger.info(f"File '{filename}' uploaded to Drive. Link: {uploaded_file.get('webViewLink')}")
        return uploaded_file.get("webViewLink")
    except Exception as e:
        logger.error(f"Error uploading file '{filename}' to Drive: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file to Google Drive: {e}")

# ✅ NEW: Function to delete a file from Google Drive
def delete_file_from_drive(file_id: str):
    """
    Deletes a file from Google Drive by its file ID.
    """
    get_drive_credentials() # Ensure credentials are valid and refreshed

    try:
        # The .delete() method returns None on success for Drive API v3
        drive_service.files().delete(fileId=file_id).execute()
        logger.info(f"File with ID '{file_id}' deleted from Google Drive.")
    except Exception as e:
        logger.error(f"Error deleting file with ID '{file_id}' from Drive: {e}")
        # If file not found, Google API returns a specific error that we can catch
        if "File not found" in str(e):
            raise HTTPException(status_code=404, detail=f"File with ID '{file_id}' not found in Google Drive or not accessible.")
        raise HTTPException(status_code=500, detail=f"Error deleting file from Google Drive: {e}")


# ✅ API endpoint to upload multiple files with authorization
@router.post("/")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    API endpoint to handle multiple file uploads to Google Drive.
    Requires authentication via a Bearer token.

    Args:
        files (List[UploadFile]): A list of files received from the client.
        credentials (HTTPAuthorizationCredentials): The authentication credentials from the request header.

    Returns:
        dict: A dictionary containing a success message and a list of Google Drive links for each uploaded file.

    Raises:
        HTTPException: If an error occurs during file saving or uploading, or if authentication fails.
    """
    # Extract token and decode to get user_id, consistent with your other routes
    token = credentials.credentials
    user_id = decode_access_token(token).get("user_id")

    if not user_id:
        logger.warning("Authentication failed: Invalid token or user_id not found.")
        raise HTTPException(status_code=401, detail="Invalid token")
    
    logger.info(f"Upload request received from authenticated user: {user_id}")

    uploaded_links = []
    for file in files:
        file_location = None
        try:
            temp_filename = f"temp_{uuid.uuid4().hex}_{file.filename}"
            file_location = os.path.join(tempfile.gettempdir(), temp_filename)

            with open(file_location, "wb") as buffer:
                contents = await file.read()
                buffer.write(contents)
            logger.info(f"Temporary file saved for '{file.filename}' at: {file_location}")

            link = upload_file_to_drive(file_location, file.filename)
            uploaded_links.append({"filename": file.filename, "link": link})

        except Exception as e:
            logger.error(f"An error occurred during upload of '{file.filename}': {e}")
            uploaded_links.append({"filename": file.filename, "error": str(e)})
        finally:
            if file_location and os.path.exists(file_location):
                try:
                    os.remove(file_location)
                    logger.info(f"Temporary file deleted for '{file.filename}': {file_location}")
                except OSError as e:
                    logger.warning(f"Could not delete temporary file {file_location} for '{file.filename}': {e}")

    if not uploaded_links:
        # If no files were provided or all failed
        if not files:
            raise HTTPException(status_code=400, detail="No files provided for upload.")
        else:
            raise HTTPException(status_code=500, detail="All files failed to upload.")

    return {"message": "File upload process completed.", "results": uploaded_links}


# ✅ NEW: API endpoint to delete a file from Google Drive
@router.delete("/{drive_file_id}")
async def delete_drive_file(
    drive_file_id: str = Path(..., description="The Google Drive File ID to delete"),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Deletes a specific file from Google Drive by its ID.
    Requires authentication via a Bearer token.
    """
    token = credentials.credentials
    user_id = decode_access_token(token).get("user_id")

    if not user_id:
        logger.warning("Authentication failed for delete request: Invalid token or user_id not found.")
        raise HTTPException(status_code=401, detail="Invalid token")

    logger.info(f"Delete request received for file ID '{drive_file_id}' from user: {user_id}")
    try:
        delete_file_from_drive(drive_file_id)
        return {"message": f"File with ID '{drive_file_id}' deleted successfully from Google Drive."}
    except HTTPException as e:
        raise e # Re-raise HTTPExceptions from delete_file_from_drive
    except Exception as e:
        logger.error(f"Unexpected error during deletion of file ID '{drive_file_id}': {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during file deletion: {e}")

