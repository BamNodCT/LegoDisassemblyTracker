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