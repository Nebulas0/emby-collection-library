import os
import requests
import time
from pathlib import Path

# Emby API configuration
EMBY_URL = "http://your-emby-server-address"
API_KEY = "your-api-key"

# Collection and library configuration
COLLECTION_NAME = "trending"
LIBRARY_PATH = "/path/to/your/library"

# Function to get the collection ID by name
def get_collection_id(collection_name):
    response = requests.get(
        f"{EMBY_URL}/emby/Collections",
        params={"api_key": API_KEY},
    )
    response.raise_for_status()
    collections = response.json().get("Items", [])
    for collection in collections:
        if collection["Name"] == collection_name:
            return collection["Id"]
    raise ValueError(f"Collection '{collection_name}' not found")

# Function to get movies in the collection
def get_collection_movies(collection_id):
    response = requests.get(
        f"{EMBY_URL}/emby/Collections/{collection_id}/Items",
        params={"api_key": API_KEY},
    )
    response.raise_for_status()
    return response.json().get("Items", [])

# Function to create symlinks for the movies
def create_symlinks(movies, library_path):
    os.makedirs(library_path, exist_ok=True)
    existing_symlinks = set(Path(library_path).iterdir())
    new_symlinks = set()

    for movie in movies:
        source_path = movie.get("Path")
        if not source_path:
            print(f"Skipping movie '{movie['Name']}' as it has no path")
            continue
        symlink_path = Path(library_path) / f"{movie['Name']}.lnk"
        new_symlinks.add(symlink_path)

        # Create symlink if it doesn't exist
        if not symlink_path.exists():
            os.symlink(source_path, symlink_path)
            print(f"Created symlink: {symlink_path}")

    # Remove outdated symlinks
    for symlink in existing_symlinks - new_symlinks:
        symlink.unlink()
        print(f"Removed outdated symlink: {symlink}")

# Main function to update the library
def update_library():
    try:
        collection_id = get_collection_id(COLLECTION_NAME)
        movies = get_collection_movies(collection_id)
        create_symlinks(movies, LIBRARY_PATH)
    except Exception as e:
        print(f"Error updating library: {e}")

# Scheduler to run the update every 6 hours
if __name__ == "__main__":
    while True:
        print("Updating library...")
        update_library()
        print("Library update complete. Waiting for 6 hours...")
        time.sleep(6 * 60 * 60)  # Wait for 6 hours
