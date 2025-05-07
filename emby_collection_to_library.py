import os
import requests
import time
import logging
from pathlib import Path

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.INFO,  # Set to logging.DEBUG for more verbosity
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]  # Logs will go to stdout
)

# Logger instance
logger = logging.getLogger(__name__)

# Emby API configuration
EMBY_URL = "http://nebula:8096"  # Replace with your Emby server address
API_KEY = "9c577d54a38e477880c294f7208c22c4"  # Replace with your Emby API key

# Collection IDs (replace with actual IDs)
MOVIE_COLLECTION_ID = "2421687"  # Replace with the Collection_ID for Movies
TV_COLLECTION_ID = "2421686"  # Replace with the Collection_ID for TV Shows

# Paths for symlinks
BASE_PATH = "/opt/emby-collection-to-library"
MEDIA_LIBRARY_PATH = f"{BASE_PATH}/library"
SYMLINK_LIBRARY_PATH_MOVIES = f"{BASE_PATH}/output/movies"
SYMLINK_LIBRARY_PATH_TV_SHOWS = f"{BASE_PATH}/output/tvshows"

# Path mapping table
PATH_MAPPING = {
    "/mnt/unionfs": "/mnt/unionfs"  # Ensure local and Emby paths match
}

def map_emby_path(emby_path):
    """
    Map Emby's path to the local system path using the PATH_MAPPING table.
    """
    for emby_base, local_base in PATH_MAPPING.items():
        if emby_path.startswith(emby_base):
            return emby_path.replace(emby_base, local_base, 1)
    return emby_path  # Return the original path if no mapping is found

# Function to fetch items in a collection using Collection_ID (for Movies)
def get_collection_items(collection_id):
    """
    Fetch all items in the specified collection by Collection_ID.
    """
    response = requests.get(
        f"{EMBY_URL}/emby/Items",
        params={"api_key": API_KEY, "ParentId": collection_id},
    )
    if response.status_code != 200:
        logger.error(f"Error fetching items for collection {collection_id}: {response.status_code} - {response.text}")
        raise ValueError(f"Failed to fetch items for collection ID {collection_id}.")
    
    return response.json().get("Items", [])

# Function to get the first episode ID for a TV show collection
def get_first_episode_id(collection_id):
    """
    Fetch all episodes for TV shows within the specified collection and return the first episode ID.
    """
    response = requests.get(
        f"{EMBY_URL}/emby/Items",
        params={
            "api_key": API_KEY,
            "ParentId": collection_id,
            "IncludeItemTypes": "Episode",
            "Recursive": True
        },
    )
    if response.status_code != 200:
        logger.error(f"Error fetching episodes for TV shows with collection ID {collection_id}: {response.status_code} - {response.text}")
        raise ValueError(f"Failed to fetch episodes for TV shows with collection ID {collection_id}.")
    
    episodes = response.json().get("Items", [])
    if not episodes:
        logger.warning(f"No episodes found for TV show collection ID {collection_id}.")
        return None
    
    return episodes[0]["Id"]  # Return the first episode ID

# Function to fetch playback info for the first episode of a TV show
def get_tv_show_path_from_episode(episode_id):
    """
    Fetch playback information for a given episode ID and adjust the path to point to the TV show directory.
    """
    response = requests.get(
        f"{EMBY_URL}/emby/Items/{episode_id}/PlaybackInfo",
        params={"api_key": API_KEY},
    )
    if response.status_code != 200:
        logger.error(f"Error fetching playback info for episode ID {episode_id}: {response.status_code} - {response.text}")
        return None

    playback_info = response.json()
    if "MediaSources" in playback_info and len(playback_info["MediaSources"]) > 0:
        full_path = playback_info["MediaSources"][0].get("Path")
        if full_path:
            # Adjust the path to only include the TV show directory
            return "/".join(full_path.split("/")[:-2]) + "/"  # Remove episode and season parts
    return None

# Function to create symlinks for Movies or TV Shows
def create_symlinks(items, library_path, item_type):
    """
    Create symbolic links for all items in the collection.
    """
    os.makedirs(library_path, exist_ok=True)
    existing_symlinks = set(Path(library_path).iterdir())
    new_symlinks = set()

    for item in items:
        if item_type == "TV Show":
            # For TV shows, get the first episode ID and use it to fetch the show path
            episode_id = get_first_episode_id(item["Id"])
            if not episode_id:
                logger.warning(f"Skipping TV Show '{item['Name']}' as no episodes are available.")
                continue

            source_path = get_tv_show_path_from_episode(episode_id)
            if not source_path:
                logger.warning(f"Skipping TV Show '{item['Name']}' as it has no valid playback path in Emby.")
                continue
        else:
            # For Movies, fetch the direct path
            source_path = item.get("Path")
            if not source_path:
                logger.warning(f"Skipping Movie '{item['Name']}' as it has no valid playback path in Emby.")
                continue
            source_path = map_emby_path(source_path)

        if not os.path.exists(source_path):
            logger.warning(f"Source path does not exist for {item_type} '{item['Name']}': {source_path}")
            continue

        symlink_path = Path(library_path) / f"{item['Name']}.lnk"
        new_symlinks.add(symlink_path)

        if not symlink_path.exists() or symlink_path.resolve() != Path(source_path).resolve():
            if symlink_path.exists():
                symlink_path.unlink()
            os.symlink(source_path, symlink_path)
            logger.info(f"Created symlink for {item_type}: {symlink_path} -> {source_path}")

    for symlink in existing_symlinks - new_symlinks:
        symlink.unlink()
        logger.info(f"Removed outdated symlink for {item_type}: {symlink}")

# Function to update the library for Movies or TV Shows
def update_library(collection_id, library_path, item_type):
    """
    Fetches the collection from Emby and updates the symlink library.
    """
    try:
        logger.info(f"Fetching {item_type} items in the collection...")
        items = get_collection_items(collection_id)
        logger.info(f"Found {len(items)} {item_type}(s) in the collection")

        logger.info(f"Creating symlinks for {item_type}...")
        create_symlinks(items, library_path, item_type)
        logger.info(f"Symlink library update for {item_type} complete.")
    except Exception as e:
        logger.error(f"Error updating {item_type} library: {e}")

# Scheduler to run the updates every 6 hours
if __name__ == "__main__":
    while True:
        logger.info("Starting library update for Movies...")
        update_library(MOVIE_COLLECTION_ID, SYMLINK_LIBRARY_PATH_MOVIES, "Movie")

        logger.info("Starting library update for TV Shows...")
        update_library(TV_COLLECTION_ID, SYMLINK_LIBRARY_PATH_TV_SHOWS, "TV Show")

        logger.info("Library update complete. Waiting for 6 hours...")
        time.sleep(6 * 60 * 60)  # Wait for 6 hours before refreshing
