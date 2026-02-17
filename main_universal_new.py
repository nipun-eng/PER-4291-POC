# from dotenv import load_dotenv
# load_dotenv()
import json 
from google import genai
import glob
import os
import re
import time

# Import all functions from web_scraper.py
from web_scraper_universal_new import run, get_multiple_urls, sync_playwright

# client = genai.Client()

# Get multiple URLs from user
urls = get_multiple_urls()

# Process each URL one by one
for i, url in enumerate(urls):
   
    print(f"Processing URL {i+1} of {len(urls)}: {url}")
  
    
    with sync_playwright() as playwright:
        run(playwright, url, True, url_index=i+1, total_urls=len(urls))
    
    # Small pause between URLs (except after the last one)
    if i < len(urls) - 1:
        print(f"\n⏸  Pausing for 3 seconds before next URL...")
        time.sleep(3)

print(f"\n{'='*60}")
print(" All URLs processed successfully!")
print(f"{'='*60}")

# Optional: Show summary of generated files
print("\nSUMMARY OF GENERATED FILES")
print("-" * 40)

# Count folders instead of individual files
data_folders = glob.glob("*_data")
screenshot_folders = glob.glob("*_screenshots")

print(f"Data folders: {len(data_folders)}")
print(f"Screenshot folders: {len(screenshot_folders)}")

if data_folders:
    print("\n📂 Data folders created:")
    for folder in data_folders:
        files = glob.glob(f"{folder}/*.json")
        print(f"  • {folder}/ ({len(files)} JSON files)")