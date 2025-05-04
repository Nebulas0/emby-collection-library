import os
import requests
import time
from pathlib import Path

# Emby API configuration
EMBY_URL = "http://your-emby-server-address"  # Replace with your Emby server address
API_KEY = "your-api-key"  # Replace with your Emby API key

# Collection names
MOVIE_COLLECTION_NAME = "trending_movies"  # Name of the collection for Movies
TV_COLLECTION_NAME = "trending_tvshows"  # Name of the collection for TV Shows

# Output paths for symlinks
SYMLINK_LIBRARY_PATH_MOVIES = "/output/library/movies"  # Path where symlinks for Movies will be created
SYMLINK_LIBRARY_PATH_TV_SHOWS = "/output/library/tvshows"  # Path where symlinks for TV Shows will be created

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

# Function to get items in the collection
def get_collection_items(collection_id):
    """
    Fetch all items in the specified collection.
    """
    response = requests.get(
        f"{EMBY_URL}/emby/Collections/{collection_id}/Items",
        params={"api_key": API_KEY},
    )
    response.raise_for_status()
    return response.json().get("Items", [])

# Function to create symlinks for Movies or TV Shows
def create_symlinks(items, library_path, item_type):
    """
    Create symbolic links for all items in the collection.
    Removes outdated symlinks and creates new ones as needed.
    """
    os.makedirs(library_path, exist_ok=True)  # Ensure library directory exists
    existing_symlinks = set(Path(library_path).iterdir())  # Track existing symlinks
    new_symlinks = set()

    for item in items:
        # Get the source path of the item from the Emby library
        source_path = item.get("Path")
        if not source_path:
            print(f"Skipping {item_type} '{item['Name']}' as it has no valid path in Emby")
            continue

        # Adjust the source path based on Docker volume mapping
        source_path = source_path.replace(EMBY_LIBRARY_PATH, "/emby/library")
        if not os.path.exists(source_path):
            print(f"Warning: Source path does not exist for {item_type} '{item['Name']}': {source_path}")
            continue

        # Create the symlink path in the output library
        symlink_path = Path(library_path) / f"{item['Name']}.lnk"
        new_symlinks.add(symlink_path)

        # Create or update the symlink if it doesn't exist
        if not symlink_path.exists() or symlink_path.resolve() != Path(source_path).resolve():
            if symlink_path.exists():
                symlink_path.unlink()  # Remove outdated symlink
            os.symlink(source_path, symlink_path)
            print(f"Created symlink for {item_type}: {symlink_path} -> {source_path}")

    # Remove outdated symlinks
    for symlink in existing_symlinks - new_symlinks:
        symlink.unlink()
        print(f"Removed outdated symlink for {item_type}: {symlink}")

# Main function to update the library for Movies or TV Shows
def update_library(collection_name, library_path, item_type):
    """
    Fetches the collection from Emby and updates the symlink library.
    """
    try:
        print(f"Fetching collection ID for {item_type}...")
        collection_id = get_collection_id(collection_name)
        print(f"Collection ID for '{collection_name}': {collection_id}")

        print(f"Fetching {item_type} items in the collection...")
        items = get_collection_items(collection_id)
        print(f"Found {len(items)} {item_type}(s) in the collection")

        print(f"Creating symlinks for {item_type}...")
        create_symlinks(items, library_path, item_type)
        print(f"Symlink library update for {item_type} complete.")
    except Exception as e:
        print(f"Error updating {item_type} library: {e}")

# Scheduler to run the update for both Movies and TV Shows every 6 hours
if __name__ == "__main__":
    while True:
        print("Starting library update for Movies...")
        update_library(MOVIE_COLLECTION_NAME, SYMLINK_LIBRARY_PATH_MOVIES, "Movie")

        print("Starting library update for TV Shows...")
        update_library(TV_COLLECTION_NAME, SYMLINK_LIBRARY_PATH_TV_SHOWS, "TV Show")

        print("Library update complete. Waiting for 6 hours...")
        time.sleep(6 * 60 * 60)  # Wait for 6 hours before refreshing
