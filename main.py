import requests
import time
import os
from colorama import Fore, Style
from dotenv import load_dotenv
from functions import *

#URL = "https://mangadex.org/title/2c891277-3d4b-4303-ad1d-e87c39a6e10c/nozoki-ana"


# Define manga page URL
print(Fore.GREEN + "Starting..." + Style.RESET_ALL)
#manga_url = URL
manga_url = input("Paste manga URL, or type 'exit' to quit: ").lower()

# Set Global Variables
manga_name = manga_url.split("/")[-1]
manga_id = extraxt_id(manga_url)

if manga_url == "":
    print(Fore.RED + "URL is required" + Style.RESET_ALL)
    exit()
elif manga_url == "exit":
    print(Fore.RED + "Exiting..." + Style.RESET_ALL)
    exit()
else:
    print(Fore.GREEN + "URL: " + manga_url + Style.RESET_ALL)

# Make directories
make_dirs(manga_url)

# Call to API to get cover art
manga_name = manga_url.split("/")[-1]
cover_art = get_cover_art(manga_id, manga_name)

# Call to API to get volumes
volumes = get_volumes(manga_id, manga_name)

# Call to API to get chapters images
chapters_images = get_chapters_images(manga_name)

# Make CBR or CBZ
make_cbr_cbz(manga_name)