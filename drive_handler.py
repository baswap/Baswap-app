import base64
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class DriveManager:
    def __init__(self, scopes=None):
        """Initialize the DriveManager with service account credentials."""
        print("[INFO] Initializing DriveManager...")

        base64_string = os.environ["SERVICE_ACCOUNT"]
        base64_bytes = base64_string.encode("ascii")

        json_bytes = base64.b64decode(base64_bytes)
        json_string = json_bytes.decode("ascii")

        if not json_string:
            raise ValueError("[ERROR] Service account information is required")

        print("[INFO] Parsing service account JSON...")
        scopes = scopes or ['https://www.googleapis.com/auth/drive']
        service_account_info = json.loads(json_string)

        print("[INFO] Creating credentials...")
        self.credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)

        print("[INFO] Building Google Drive service...")
        self.drive_service = build('drive', 'v3', credentials=self.credentials)

        print("[INFO] DriveManager initialized successfully.")

    def create_folder(self, folder_name, parent_folder_id=None):
        """Create a folder in Google Drive and return its ID."""
        print(f"[INFO] Creating folder '{folder_name}'...")
        folder_metadata = {
            'name': folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            'parents': [parent_folder_id] if parent_folder_id else []
        }

        created_folder = self.drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()

        print(f"[SUCCESS] Folder '{folder_name}' created with ID: {created_folder['id']}")
        return created_folder["id"]

    def upload_file(self, file_path, folder_id=None):
        """Upload a file to Google Drive."""
        print(f"[INFO] Uploading file '{file_path}'...")
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id] if folder_id else []
        }

        print(f"[INFO] Preparing file upload metadata and media...")
        media = MediaFileUpload(file_path, mimetype='text/csv')

        uploaded_file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        print(f"[SUCCESS] File '{os.path.basename(file_path)}' uploaded with ID: {uploaded_file['id']}")
        return uploaded_file['id']

    def list_files(self, folder_id=None):
        """List files in a folder or in the root directory if no folder is specified."""
        print("[INFO] Listing files...")
        query = f"'{folder_id}' in parents and trashed=false" if folder_id else "trashed=false"
        
        results = self.drive_service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()

        files = results.get('files', [])
        if files:
            print("[SUCCESS] Files retrieved:")
            for file in files:
                print(f"  - Name: {file['name']}, ID: {file['id']}, Type: {file['mimeType']}")
        else:
            print("[INFO] No files found.")
        return files

    def delete_file(self, file_id):
        """Delete a file or folder by ID."""
        print(f"[INFO] Deleting file/folder with ID: {file_id}...")
        try:
            self.drive_service.files().delete(fileId=file_id).execute()
            print(f"[SUCCESS] Successfully deleted file/folder with ID: {file_id}")
        except Exception as e:
            print(f"[ERROR] Failed to delete file/folder with ID: {file_id}. Error: {str(e)}")
