import os

CAMERA_API = os.environ.get("CAMERA_API", "http://localhost:4444")

BRICKTRACKER = os.environ.get("BRICKTRACKER","/workspaces/legoscanner/bricktracker")
BRICKTRACKER_DB = os.environ.get("BRICKTRACKER_DB", f"{BRICKTRACKER}/app.db")
IMAGE_FOLDER = os.environ.get("IMAGE_FOLDER",f"{BRICKTRACKER}/parts")

BRICKOGNIZE_API = "https://api.brickognize.com"
