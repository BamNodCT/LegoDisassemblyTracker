"""
Helpful code chunks
"""
# Imports
import streamlit as st
from studs import settings
from studs import databasemanager

## IP Camera
cameraURL = settings.CAMERA_API
## ImagePath
imagesLocation = settings.IMAGE_FOLDER
## Bricktracker DB
bricktrackerDB = settings.BRICKTRACKER_DB

## DataBase Connection
db = databasemanager.DatabaseManager(bricktrackerDB)

 # Test Connection
def test_db():
    """Test Database Connection
    Args:
        db (databasemanager): Database to check
    Returns:
        Dictionary: Test Results
    """
    results = {
                "BT":False,
                "Sets":False,
                "DT":False,
              }
    try:
        results["BT"] = db.table_exists('bricktracker_sets')

        query = ''' 
                select 1
                from bricktracker_sets
                limit 1
                '''
        results["Sets"] = not db.query_df(query).empty
        results["DT"] = db.table_exists('disassembly_tracker')
    except (FileNotFoundError,ValueError):
        results["BT"] = False

    return results