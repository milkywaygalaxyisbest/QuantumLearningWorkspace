# Architecture Notes

## Data Layer

The backend will use MongoDB Atlas as the primary database for file-related metadata.

### Chosen database
- MongoDB Atlas is the selected database for persistence.
- The backend connects through a dedicated database module so the API layer remains independent from storage details.

### Upload schema
A simple Upload document will include:
- filename: original uploaded file name
- upload_date: timestamp of the upload
- file_type: MIME type or file extension category
- status: current upload state such as uploaded, processing, or completed
- metadata: optional extra information for future expansion

### Backend files
- web/backend/database.py: manages the MongoDB connection and collection access
- web/backend/models.py: defines the Upload schema model

### Environment variables
The application should be configured with:
- MONGODB_URI: Atlas connection string
- MONGODB_DB_NAME: target database name
