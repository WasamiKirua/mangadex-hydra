import requests
import os
import json
import asyncio
import aiohttp
import re
from colorama import Fore, Style
from dotenv import load_dotenv
from time import sleep, time
from math import ceil
from tqdm import tqdm
import shutil
import zipfile
import patoolib
from pathlib import Path

load_dotenv()

# Proxy configuration with login and password
proxy_host = 'gw.dataimpulse.com'
proxy_port = 823
proxy_login = os.getenv('DATA_IMPULSE_LOGIN')
proxy_password = os.getenv('DATA_IMPULSE_PASSWD')
proxy = f'http://{proxy_login}:{proxy_password}@{proxy_host}:{proxy_port}'

# Proxy rotation time in seconds
PROXY_ROTATION_TIME = 15

proxies = {
    'http': proxy,
    'https': proxy
}

# Track the last proxy rotation time
last_rotation_time = time()

def sleep_(time):
    sleep(time)

def make_dirs(url):
    manga_name = url.split("/")[-1]

    print(Fore.GREEN + "Creating directories..." + Style.RESET_ALL)
    print(manga_name)
    os.makedirs(f'data/{manga_name}', exist_ok=True)
    os.makedirs(f'data/{manga_name}/json', exist_ok=True)
    os.makedirs(f'data/{manga_name}/volumes', exist_ok=True)

def extraxt_id(url):
    manga_id = url.split("/")[-2]
    return manga_id

def get_cover_art(manga_id, manga_name):
    # Wait 3 seconds to avoid rate limiting
    sleep_(3)
    base_url = f"https://api.mangadex.org/manga/{manga_id}?includes[]=artist&includes[]=author&includes[]=cover_art"
    response = requests.get(base_url)

    # Check if the request was successful
    if response.status_code == 200:
        # Process the response content
        with open(f'data/{manga_name}/json/cover_art.json', 'w') as f:
            json.dump(response.json(), f, indent=2)
        print(f'{Fore.GREEN}Cover Art saved{Style.RESET_ALL}')
    else:
        print(f'{Fore.RED}Cover Art Request failed with status code: {response.status_code}{Style.RESET_ALL}')

    # Download the cover art
    with open(f'data/{manga_name}/json/cover_art.json', 'r') as f:
        cover_art = json.load(f)
        
        for cover_art_id in cover_art['data']['relationships']:
            if cover_art_id['type'] == 'cover_art':
                cover_art_jpg = cover_art_id['attributes']['fileName']
                cover_art_url = f'https://mangadex.org/covers/{manga_id}/{cover_art_jpg}.512.jpg'

        # Download the cover art
        response = requests.get(cover_art_url)
        if response.status_code == 200:
            with open(f'data/{manga_name}/cover_art.jpg', 'wb') as f:
                f.write(response.content)
            print(f'{Fore.GREEN}Cover Art saved{Style.RESET_ALL}')
        else:
            print(f'{Fore.RED}Cover Art Request failed with status code: {response.status_code}{Style.RESET_ALL}')


def get_volumes(manga_id, manga_name):
    # Wait 3 seconds to avoid rate limiting
    sleep_(3)
    base_url = f"https://api.mangadex.org/manga/{manga_id}/aggregate?translatedLanguage%5B%5D=en"
    response = requests.get(base_url)

    # Check if the request was successful
    if response.status_code == 200:
        # Process the response content
        with open(f'data/{manga_name}/json/volumes.json', 'w') as f:
            json.dump(response.json(), f, indent=2)
        print(f'{Fore.GREEN}Volumes saved{Style.RESET_ALL}')
    else:
        print(f'{Fore.RED}Volumes Request failed with status code: {response.status_code}{Style.RESET_ALL}')


def get_chapters_image_data(chapter_id, manga_name, volume, chapter):
    # Wait 5 seconds to avoid rate limiting
    sleep_(5)

    base_url = f"https://api.mangadex.org/at-home/server/{chapter_id}?forcePort443=false"
    print(f'{Fore.CYAN}Volume: {volume} {Style.RESET_ALL} {Fore.YELLOW}Chapter: {chapter} {Style.RESET_ALL}{Fore.MAGENTA} Getting image data{Style.RESET_ALL}')
    print()
    response = requests.get(base_url)
    if response.status_code == 200:
        with open(f'data/{manga_name}/json/volumes/{volume}/chapters/{chapter}/image_data.json', 'w') as f:
            json.dump(response.json(), f, indent=2)
        print(f'{Fore.GREEN}Image data saved{Style.RESET_ALL}')
        print()
    else:
        print(f'{Fore.RED}Image Data Request failed with status code: {response.status_code}{Style.RESET_ALL}')


async def download_single_image(session, image_base_url, save_path, proxies=None, max_retries=3, retry_delay=5):
    for attempt in range(max_retries):
        try:
            async with session.get(image_base_url, proxy=proxies.get('http') if proxies else None) as response:
                if response.status == 200:
                    with open(save_path, 'wb') as f:
                        f.write(await response.read())
                    return True
                else:
                    print(f'{Fore.RED}Failed to download image (Attempt {attempt + 1}/{max_retries}): Status {response.status}{Style.RESET_ALL}')
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
        except Exception as e:
            if 'NO_HOST_CONNECTION' in str(e):
                print(f'{Fore.RED}Proxy connection failed (Attempt {attempt + 1}/{max_retries}). Retrying...{Style.RESET_ALL}')
            else:
                print(f'{Fore.RED}Error downloading image (Attempt {attempt + 1}/{max_retries}): {str(e)}{Style.RESET_ALL}')
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
    return False


async def process_batch(session, batch, manga_name, volume, chapter, base_url, hash, proxies=None):
    if len(batch) > 15:  # Safety check
        print(f'{Fore.YELLOW}Warning: Batch size exceeds 15, this should not happen{Style.RESET_ALL}')
        
    tasks = []
    failed_downloads = []
    
    for image in batch:
        image_base_url = f'{base_url}/data/{hash}/{image}'
        save_path = f'data/{manga_name}/volumes/{volume}/{chapter}/{image}'
        print(f'{Fore.CYAN}Volume: {volume} {Style.RESET_ALL} {Fore.YELLOW}Chapter: {chapter} {Style.RESET_ALL}{Fore.MAGENTA} Downloading image: {image}{Style.RESET_ALL}')
        task = download_single_image(session, image_base_url, save_path, proxies)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    # Check for failed downloads
    for i, success in enumerate(results):
        if not success:
            failed_downloads.append(batch[i])
    
    if failed_downloads:
        print(f'{Fore.RED}Failed to download {len(failed_downloads)} images from this batch after all retries{Style.RESET_ALL}')
        for failed_image in failed_downloads:
            print(f'{Fore.RED}Failed image: {failed_image}{Style.RESET_ALL}')
    
    return results


def download_images(manga_name, volume, chapter):
    # Get the batch size
    batch_size = os.getenv('BATCH_SIZE')
    
    with open(f'data/{manga_name}/json/volumes/{volume}/chapters/{chapter}/image_data.json', 'r') as f:
        image_data = json.load(f)
    base_url = image_data['baseUrl']
    hash = image_data['chapter']['hash']
    images_list = image_data['chapter']['data']

    # Check if proxy should be used
    use_proxy = os.getenv('WITH_PROXY', 'no').lower() == 'yes'
    current_proxies = proxies if use_proxy else None

    # Calculate number of batches
    num_batches = ceil(len(images_list) / batch_size)
    print(f'{Fore.BLUE}Processing {len(images_list)} images in {num_batches} batches of max {batch_size} images each{Style.RESET_ALL}')
    
    async def main():
        global last_rotation_time
        async with aiohttp.ClientSession() as session:
            for i in range(num_batches):
                start_idx = i * batch_size
                end_idx = min((i + 1) * batch_size, len(images_list))
                current_batch = images_list[start_idx:end_idx]
                
                print(f'{Fore.BLUE}Processing batch {i + 1}/{num_batches} ({len(current_batch)} images){Style.RESET_ALL}')
                
                # If using proxy, align with rotation time
                if use_proxy:
                    current_time = time()
                    time_since_last_rotation = current_time - last_rotation_time
                    if time_since_last_rotation < PROXY_ROTATION_TIME:
                        wait_time = PROXY_ROTATION_TIME - time_since_last_rotation
                        print(f'{Fore.YELLOW}Waiting {wait_time:.2f} seconds for proxy rotation{Style.RESET_ALL}')
                        await asyncio.sleep(wait_time)
                    last_rotation_time = time()
                else:
                    # Keep 10 seconds delay if not using proxy
                    if i < num_batches - 1:
                        await asyncio.sleep(5)
                
                # Process the current batch
                await process_batch(session, current_batch, manga_name, volume, chapter, base_url, hash, current_proxies)

    # Run the async download process
    asyncio.run(main())


def get_chapters_images(manga_name):
    # Get the volumes
    with open(f'data/{manga_name}/json/volumes.json', 'r') as f:
        volumes = json.load(f)

    # Get the chapters
    for volume in volumes['volumes']:
        # Make the directory for the volume
        os.makedirs(f'data/{manga_name}/volumes/{volume}', exist_ok=True)
        print(f'{Fore.CYAN}Volume: {volume} {Style.RESET_ALL}{Fore.GREEN} folder created{Style.RESET_ALL}')
        print()
        for chapter in volumes['volumes'][volume]['chapters']:
            # Make the directory for the chapter image and json
            os.makedirs(f'data/{manga_name}/volumes/{volume}/{chapter}', exist_ok=True)
            print(f'{Fore.CYAN}Volume: {volume} {Style.RESET_ALL} {Fore.YELLOW}Chapter: {chapter} {Style.RESET_ALL}{Fore.GREEN} folder created{Style.RESET_ALL}')
            print()
            # Make the directory for the chapter image and json
            os.makedirs(f'data/{manga_name}/json/volumes/{volume}/chapters/{chapter}', exist_ok=True)
            print(f'{Fore.CYAN}Volume: {volume} {Style.RESET_ALL} {Fore.YELLOW}Chapter: {chapter} {Style.RESET_ALL}{Fore.GREEN} folder json created{Style.RESET_ALL}')
            print()
            # Get the chapter ID
            chapter_id = volumes['volumes'][volume]['chapters'][chapter]['id']
            print(f'{Fore.CYAN}Volume: {volume} {Style.RESET_ALL} {Fore.YELLOW}Chapter: {chapter} {Style.RESET_ALL}{Fore.MAGENTA} Chapter ID: {chapter_id}{Style.RESET_ALL}')
            print()
            # Get the image data
            get_chapters_image_data(chapter_id, manga_name, volume, chapter)
            # Download the images
            download_images(manga_name, volume, chapter)


def make_cbr_cbz(manga_name):
    try:
        # Ask user for format preference
        while True:
            format_choice = input("Choose format (cbr/cbz): ").lower()
            if format_choice in ['cbr', 'cbz']:
                break
            print(f'{Fore.RED}Please choose either "cbr" or "cbz"{Style.RESET_ALL}')

        # Create temporary directory for organizing files
        temp_dir = f'data/{manga_name}/temp/{manga_name}'
        os.makedirs(temp_dir, exist_ok=True)

        # Get and sort volume list numerically
        try:
            volume_list = sorted(
                os.listdir(f'data/{manga_name}/volumes'),
                key=lambda x: float(x)  # Preserve numerical ordering
            )
        except Exception as e:
            print(f'{Fore.RED}Error reading volumes: {str(e)}{Style.RESET_ALL}')
            return

        if not volume_list:
            print(f'{Fore.RED}No volumes found for {manga_name}{Style.RESET_ALL}')
            return

        # Copy cover art if exists
        if os.path.exists(f'data/{manga_name}/cover_art.jpg'):
            try:
                shutil.copy2(
                    f'data/{manga_name}/cover_art.jpg',
                    f'{temp_dir}/000-cover.jpg'  # Ensure cover is first
                )
                print(f'{Fore.GREEN}Cover art added{Style.RESET_ALL}')
            except Exception as e:
                print(f'{Fore.YELLOW}Warning: Could not copy cover art: {str(e)}{Style.RESET_ALL}')

        # Process volumes with progress bar
        for volume in tqdm(volume_list, desc="Processing Volumes", unit="volume"):
            try:
                volume_dir = f'{temp_dir}/Volume_{volume.zfill(2)}'  # Pad volume number
                os.makedirs(volume_dir, exist_ok=True)

                # Get and sort chapters numerically
                chapter_list = sorted(
                    os.listdir(f'data/{manga_name}/volumes/{volume}'),
                    key=lambda x: float(x)  # Preserve numerical ordering for chapters
                )

                # Process chapters with progress bar
                for chapter in tqdm(chapter_list, desc=f"Volume {volume} Chapters", unit="chapter", leave=False):
                    try:
                        chapter_dir = f'{volume_dir}/Chapter_{chapter.zfill(3)}'  # Pad chapter number
                        os.makedirs(chapter_dir, exist_ok=True)

                        # Get and sort images
                        image_list = os.listdir(f'data/{manga_name}/volumes/{volume}/{chapter}')
                        sorted_images = sorted(
                            image_list,
                            key=lambda x: int(re.match(r'x(\d+)-', x).group(1))  # Preserve image ordering
                        )

                        # Copy images with progress bar
                        for idx, image in enumerate(tqdm(sorted_images, desc=f"Images", unit="img", leave=False), 1):
                            try:
                                src = f'data/{manga_name}/volumes/{volume}/{chapter}/{image}'
                                dst = f'{chapter_dir}/{idx:03d}.{image.split(".")[-1]}'
                                shutil.copy2(src, dst)
                            except Exception as e:
                                print(f'{Fore.YELLOW}Warning: Failed to copy image {image}: {str(e)}{Style.RESET_ALL}')

                    except Exception as e:
                        print(f'{Fore.YELLOW}Warning: Error processing chapter {chapter}: {str(e)}{Style.RESET_ALL}')
                        continue

            except Exception as e:
                print(f'{Fore.YELLOW}Warning: Error processing volume {volume}: {str(e)}{Style.RESET_ALL}')
                continue

        # Create final archive
        archive_path = f'data/{manga_name}/{manga_name}.{format_choice}'
        print(f'{Fore.BLUE}Creating {format_choice.upper()} archive...{Style.RESET_ALL}')

        try:
            if format_choice == 'cbz':
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    source_dir = Path(temp_dir)
                    # Get all files and sort them to ensure consistent ordering
                    all_files = sorted(
                        list(source_dir.rglob('*')),
                        key=lambda x: str(x)  # Sort paths as strings to maintain hierarchy
                    )
                    for file_path in tqdm(all_files, desc="Adding to ZIP", unit="file"):
                        if file_path.is_file():
                            arcname = str(file_path.relative_to(source_dir.parent))
                            zipf.write(file_path, arcname)
            else:  # cbr
                patoolib.create_archive(archive_path, [temp_dir])

            print(f'{Fore.GREEN}Successfully created {archive_path}{Style.RESET_ALL}')

        except Exception as e:
            print(f'{Fore.RED}Error creating archive: {str(e)}{Style.RESET_ALL}')
            return

        # Clean up temporary directory
        try:
            shutil.rmtree(Path(temp_dir).parent)
            print(f'{Fore.GREEN}Cleanup completed{Style.RESET_ALL}')
        except Exception as e:
            print(f'{Fore.YELLOW}Warning: Error during cleanup: {str(e)}{Style.RESET_ALL}')

    except Exception as e:
        print(f'{Fore.RED}Fatal error: {str(e)}{Style.RESET_ALL}')
    finally:
        # Ensure temp directory is removed even if an error occurs
        try:
            if os.path.exists(Path(temp_dir).parent):
                shutil.rmtree(Path(temp_dir).parent)
        except:
            pass
