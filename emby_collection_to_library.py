import os
import requests
import time
from pathlib import Path

# Emby API configuration
EMBY_URL = "http://your-emby-server-address"  # Replace with your Emby server address
API_KEY = "your-api-key"  # Replace with your Emby API key

# Collection and library configuration
COLLECTION_NAME = "trending"  # Name of the collection to process
SYMLINK_LIBRARY_PATH = "/output/library"  # Path where symlinks will be created

# Emby library base path inside the container (mapped via Docker volume)
EMBY_LIBRARY_PATH = "/emby/library"  # Path to the Emby library inside the container

# Function to get the collection ID by name
def get_collection_id(collection_name):
    """
    Fetch the collection ID from Emby by its name.
    """
    response = requests.get(
        f"{EMBY_URL}/emby/Collections",
        params={"api_key": API_KEY},
    )
    response.raise_for_status()
    collections = response.json().get("Items", [])
    for collection in collections:
        if collection["Name"].lower() == collection_name.lower():
            return collection["Id"]
    raise ValueError(f"Collection '{collection_name}' not found")

# Function to get movies/items in the collection
def get_collection_movies(collection_id):
    """
    Fetch all items in the specified collection.
    """
    response = requests.get(
        f"{EMBY_URL}/emby/Collections/{collection_id}/Items",
        params={"api_key": API_KEY},
    )
    response.raise_for_status()
    return response.json().get("Items", [])

# Function to create symlinks for the movies/items
def create_symlinks(movies, library_path):
    """
    Create symbolic links for all movies/items in the collection.
    Removes outdated symlinks and creates new ones as needed.
    """
    os.makedirs(library_path, exist_ok=True)  # Ensure library directory exists
    existing_symlinks = set(Path(library_path).iterdir())  # Track existing symlinks
    new_symlinks = set()

    for movie in movies:
        # Get the source path of the movie from the Emby library
        source_path = movie.get("Path")
        if not source_path:
            print(f"Skipping movie '{movie['Name']}' as it has no valid path in Emby")
            continue

        # Adjust the source path based on Docker volume mapping
        source_path = source_path.replace(EMBY_LIBRARY_PATH, "/emby/library")
        if not os.path.exists(source_path):
            print(f"Warning: Source path does not exist for '{movie['Name']}': {source_path}")
            continue

        # Create the symlink path in the output library
        symlink_path = Path(library_path) / f"{movie['Name']}.lnk"
        new_symlinks.add(symlink_path)

        # Create or update the symlink if it doesn't exist
        if not symlink_path.exists() or symlink_path.resolve() != Path(source_path).resolve():
            if symlink_path.exists():
                symlink_path.unlink()  # Remove outdated symlink
            os.symlink(source_path, symlink_path)
            print(f"Created symlink: {symlink_path} -> {source_path}")

    # Remove outdated symlinks
    for symlink in existing_symlinks - new_symlinks:
        symlink.unlink()
        print(f"Removed outdated symlink: {symlink}")

# Main function to update the library
def update_library():
    """
    Fetches the collection from Emby and updates the symlink library.
    """
    try:
        print("Fetching collection ID...")
        collection_id = get_collection_id(COLLECTION_NAME)
        print(f"Collection ID for '{COLLECTION_NAME}': {collection_id}")

        print("Fetching collection items...")
        movies = get_collection_movies(collection_id)
        print(f"Found {len(movies)} items in the collection")

        print("Creating symlinks...")
        create_symlinks(movies, SYMLINK_LIBRARY_PATH)
        print("Symlink library update complete.")
    except Exception as e:
        print(f"Error updating library: {e}")

# Scheduler to run the update every 6 hours
if __name__ == "__main__":
    while True:
        print("Starting library update...")
        update_library()
        print("Library update complete. Waiting for 6 hours...")
        time.sleep(6 * 60 * 60)  # Wait for 6 hours before refreshing
