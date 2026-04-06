"""
Azure Blob Storage utilities for Doctor-Patient App
Handles encrypted PDF uploads to specific containers
"""

import os
import json
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import AzureError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")


class AzureStorageManager:
    def __init__(self):
        """Initialize Azure Storage client"""
        try:
            # Read the connection string from environment variables only.
            self.connection_string = AZURE_STORAGE_CONNECTION_STRING
            
            if not self.connection_string:
                raise ValueError("AZURE_STORAGE_CONNECTION_STRING is not set")
            
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            logger.info("Azure Storage client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Storage client: {e}")
            raise

    def upload_research_pdf(self, pdf_content, filename, patient_problem=None, metadata=None):
        """
        Upload research PDF to contoso container under pces/documents/research/
        
        Args:
            pdf_content: PDF file content (bytes)
            filename: Name of the PDF file
            patient_problem: Patient problem text for metadata
            metadata: Additional metadata dictionary
        
        Returns:
            str: Blob URL if successful, None if failed
        """
        try:
            container_name = "contoso"
            blob_path = f"pces/documents/research/{filename}"
            
            # Prepare metadata
            blob_metadata = {
                'upload_date': datetime.now().isoformat(),
                'file_type': 'research_pdf',
                'patient_problem': patient_problem or 'Not specified',
                'content_length': str(len(pdf_content))
            }
            
            # Add custom metadata if provided
            if metadata:
                # Convert all metadata values to strings for Azure compatibility
                for key, value in metadata.items():
                    blob_metadata[key] = str(value) if value is not None else ''
            
            # Create container if it doesn't exist
            container_client = self.blob_service_client.get_container_client(container_name)
            try:
                container_client.create_container()
                logger.info(f"Created container: {container_name}")
            except AzureError:
                # Container already exists
                pass
            
            # Upload with encryption (server-side encryption is enabled by default)
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_path
            )
            
            # Set content settings
            content_settings = ContentSettings(content_type='application/pdf')
            
            # Upload the blob
            blob_client.upload_blob(
                data=pdf_content,
                overwrite=True,
                metadata=blob_metadata,
                content_settings=content_settings
            )
            
            blob_url = blob_client.url
            logger.info(f"Research PDF uploaded successfully: {blob_url}")
            
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to upload research PDF: {e}")
            return None

    def upload_patient_summary_pdf(self, pdf_content, filename, patient_data=None, metadata=None):
        """
        Upload patient summary PDF to contoso container under pces/documents/doc-patient-summary/
        
        Args:
            pdf_content: PDF file content (bytes)
            filename: Name of the PDF file
            patient_data: Patient information dictionary
            metadata: Additional metadata dictionary
        
        Returns:
            str: Blob URL if successful, None if failed
        """
        try:
            container_name = "contoso"
            blob_path = f"pces/documents/doc-patient-summary/{filename}"
            
            # Prepare metadata
            blob_metadata = {
                'upload_date': datetime.now().isoformat(),
                'file_type': 'patient_summary_pdf',
                'content_length': str(len(pdf_content))
            }
            
            # Add patient data to metadata if provided
            if patient_data:
                blob_metadata.update({
                    'patient_name': str(patient_data.get('patient_name', 'Unknown')),
                    'patient_id': str(patient_data.get('patient_id', 'Unknown')),
                    'doctor_name': str(patient_data.get('doctor_name', 'Unknown')),
                    'session_date': str(patient_data.get('session_date', ''))
                })
            
            # Add custom metadata if provided
            if metadata:
                # Convert all metadata values to strings for Azure compatibility
                for key, value in metadata.items():
                    blob_metadata[key] = str(value) if value is not None else ''
            
            # Create container if it doesn't exist
            container_client = self.blob_service_client.get_container_client(container_name)
            try:
                container_client.create_container()
                logger.info(f"Created container: {container_name}")
            except AzureError:
                # Container already exists
                pass
            
            # Upload with encryption
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_path
            )
            
            # Set content settings
            content_settings = ContentSettings(content_type='application/pdf')
            
            # Upload the blob
            blob_client.upload_blob(
                data=pdf_content,
                overwrite=True,
                metadata=blob_metadata,
                content_settings=content_settings
            )
            
            blob_url = blob_client.url
            logger.info(f"Patient summary PDF uploaded successfully: {blob_url}")
            
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to upload patient summary PDF: {e}")
            return None

    def upload_conversation_pdf(self, pdf_content, filename, conversation_data=None, metadata=None):
        """
        Upload doctor-patient conversation PDF to contoso container under pces/documents/conversation/
        
        Args:
            pdf_content: PDF file content (bytes)
            filename: Name of the PDF file
            conversation_data: Conversation information dictionary
            metadata: Additional metadata dictionary
        
        Returns:
            str: Blob URL if successful, None if failed
        """
        try:
            container_name = "contoso"
            blob_path = f"pces/documents/conversation/{filename}"
            
            # Prepare metadata
            blob_metadata = {
                'upload_date': datetime.now().isoformat(),
                'file_type': 'conversation_pdf',
                'content_length': str(len(pdf_content))
            }
            
            # Add conversation data to metadata if provided
            if conversation_data:
                blob_metadata.update({
                    'doctor_name': str(conversation_data.get('doctor_name', 'Unknown')),
                    'patient_name': str(conversation_data.get('patient_name', 'Unknown')),
                    'conversation_duration': str(conversation_data.get('duration', 'Unknown')),
                    'session_date': str(conversation_data.get('session_date', ''))
                })
            
            # Add custom metadata if provided
            if metadata:
                # Convert all metadata values to strings for Azure compatibility
                for key, value in metadata.items():
                    blob_metadata[key] = str(value) if value is not None else ''
            
            # Create container if it doesn't exist
            container_client = self.blob_service_client.get_container_client(container_name)
            try:
                container_client.create_container()
                logger.info(f"Created container: {container_name}")
            except AzureError:
                # Container already exists
                pass
            
            # Upload with encryption
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_path
            )
            
            # Set content settings
            content_settings = ContentSettings(content_type='application/pdf')
            
            # Upload the blob
            blob_client.upload_blob(
                data=pdf_content,
                overwrite=True,
                metadata=blob_metadata,
                content_settings=content_settings
            )
            
            blob_url = blob_client.url
            logger.info(f"Conversation PDF uploaded successfully: {blob_url}")
            
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to upload conversation PDF: {e}")
            return None


# Initialize global storage manager
storage_manager = None

def get_storage_manager():
    """Get or create storage manager instance"""
    global storage_manager
    if storage_manager is None:
        storage_manager = AzureStorageManager()
    return storage_manager
