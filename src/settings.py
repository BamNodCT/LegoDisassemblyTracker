import os

CAMERA_API = os.environ.get("CAMERA_API", "http://localhost:4444")
BRICKTRACKER_DB = os.environ.get("BRICKTRACKER_DB", "/workspaces/legoscanner/bricktracker/app.db")
BRICKOGNIZE_API = "https://api.brickognize.com"
IMAGE_FOLDER = os.environ.get("IMAGE_FOLDER","/workspaces/legoscanner/bricktracker/parts")