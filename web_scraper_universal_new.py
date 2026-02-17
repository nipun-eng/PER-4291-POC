import re
from playwright.sync_api import sync_playwright
import json
from urllib.parse import urljoin
import time
import os
from auth_handler import AuthHandler

# Initialize auth handler
auth_handler = AuthHandler()

# ===== ALL FUNCTION DEFINITIONS FIRST =====

def __safe_filename_from(title):
    """Convert title to safe filename (without extension)"""
    safe_title = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")
    return safe_title


def __create_page_folder(title):
    """Create a folder for all data related to this page"""
    base_name = __safe_filename_from(title)
    folder_name = f"{base_name}_data"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def __ensure_screenshot_folder(base_filename):
    """Create and return path to screenshot folder"""
    folder_name = f"{base_filename}_screenshots"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def __save_page_text(page, selector, folder_path):
    """Save page text to file in specified folder"""
    title = page.title()
    content = page.query_selector(selector)
    text = (
        content.inner_text() if content else "No requested selector found"
    )

    filename = os.path.join(folder_path, f"page_text.txt")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n")
        f.write(f"URL: {page.url}\n\n")
        f.write(text)

    print(f"📄 Page text saved to {filename}")


def __capture_screenshot(page, folder_path):
    """Single screenshot saved in specified folder"""
    time.sleep(5)
    filename = os.path.join(folder_path, "screenshot.png")
    page.screenshot(path=filename, full_page=True)
    print(f"📸 Screenshot saved as {filename}")


def __capture_multiple_screenshots(page, num_screenshots=5, scroll_pause=1):
    """Take multiple screenshots while scrolling and save in organized folder"""
    
    # Get the page title for filename base
    base_filename = __safe_filename_from(page.title())
    
    # Create screenshot folder
    screenshot_folder = __ensure_screenshot_folder(base_filename)
    print(f"\n📁 Saving screenshots to: {screenshot_folder}/")
    
    # Get page height for logging
    page_height = page.evaluate("document.body.scrollHeight")
    viewport_height = page.viewport_size['height']
    print(f"\n Page height: {page_height}px, Viewport height: {viewport_height}px")
    print(f"Taking {num_screenshots} screenshots while scrolling...")
    
    for i in range(num_screenshots):
        # Calculate scroll position
        if num_screenshots > 1:
            scroll_progress = i / (num_screenshots - 1)
            scroll_y = int((page_height - viewport_height) * scroll_progress)
        else:
            scroll_y = 0
        
        # Scroll to position
        if i > 0:
            page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
            print(f"  Scrolling to position {scroll_y}px...")
            time.sleep(scroll_pause)
        
        # Take screenshot and save in folder
        filename = os.path.join(screenshot_folder, f"screenshot_{i+1}.png")
        page.screenshot(path=filename, full_page=False)
        print(f"Screenshot {i+1}/{num_screenshots} saved")
    
    # Full page screenshot
    full_filename = os.path.join(screenshot_folder, "full_page.png")
    page.screenshot(path=full_filename, full_page=True)
    print(f"\n Full page screenshot saved in folder")
    
    return screenshot_folder


def __scrape_headlines(page, folder_path):
    """Extract all headlines and save to folder"""
    headlines = []
    
    # Add small wait to ensure page is stable
    time.sleep(1)
    
    for heading_type in ['h1', 'h2', 'h3']:
        elements = page.query_selector_all(heading_type)
        for elem in elements:
            headlines.append({
                'type': heading_type,
                'text': elem.inner_text().strip()
            })
    
    filename = os.path.join(folder_path, "headlines.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(headlines, f, indent=2, ensure_ascii=False)
    
    print(f"📰 Found {len(headlines)} headlines, saved to {filename}")
    print("\n HEADLINES FOUND:")
    for h in headlines[:5]:
        print(f"  {h['type']}: {h['text'][:50]}...")
    
    return headlines


def __scrape_images(page, base_url, folder_path):
    """Extract all images and their metadata, save to folder"""
    images = []
    
    # Find all img elements
    img_elements = page.query_selector_all('img')
    
    for i, img in enumerate(img_elements):
        # Get basic attributes
        src = img.get_attribute('src')
        alt = img.get_attribute('alt') or "No alt text"
        width = img.get_attribute('width')
        height = img.get_attribute('height')
        
        # Skip if no src
        if not src:
            continue
            
        # Convert relative URLs to absolute
        if not src.startswith(('http://', 'https://')):
            src = urljoin(base_url, src)
        
        # Get image dimensions
        bounding_box = img.bounding_box()
        
        image_info = {
            'index': i,
            'src': src,
            'alt': alt,
            'width': width,
            'height': height,
            'rendered_width': bounding_box['width'] if bounding_box else None,
            'rendered_height': bounding_box['height'] if bounding_box else None,
            'visible': img.is_visible()
        }
        
        images.append(image_info)
    
    # Save image metadata
    filename = os.path.join(folder_path, "images.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(images, f, indent=2, ensure_ascii=False)
    
    print(f"🖼️  Found {len(images)} images, metadata saved to {filename}")
    
    # Display summary
    print("\n IMAGES FOUND:")
    for img in images[:5]:
        print(f"  • {img['alt'][:30]}... ({img['src'][:50]}...)")
    
    return images


def __scrape_metadata(page, folder_path):
    """Extract all meta tags and save to folder"""
    metadata = {}
    
    metadata['title'] = page.title()
    metadata['url'] = page.url
    
    # Description meta
    description = page.query_selector('meta[name="description"]')
    metadata['description'] = description.get_attribute('content') if description else None
    
    # Keywords meta
    keywords = page.query_selector('meta[name="keywords"]')
    metadata['keywords'] = keywords.get_attribute('content') if keywords else None
    
    # Author meta
    author = page.query_selector('meta[name="author"]')
    metadata['author'] = author.get_attribute('content') if author else None
    
    # Open Graph tags
    og_tags = page.query_selector_all('meta[property^="og:"]')
    metadata['og_tags'] = {}
    for tag in og_tags:
        property_name = tag.get_attribute('property')
        content = tag.get_attribute('content')
        if property_name and content:
            metadata['og_tags'][property_name] = content
    
    # Canonical URL
    canonical = page.query_selector('link[rel="canonical"]')
    metadata['canonical'] = canonical.get_attribute('href') if canonical else None
    
    # Language
    html_tag = page.query_selector('html')
    metadata['language'] = html_tag.get_attribute('lang') if html_tag else None
    
    # Save metadata
    filename = os.path.join(folder_path, "metadata.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"📋 Metadata saved to {filename}")
    return metadata


def __scrape_all_links(page, base_url, folder_path):
    """Extract all links and save to folder"""
    links = {
        'internal': [],
        'external': [],
        'navigation': [],
        'social': []
    }
    
    all_links = page.query_selector_all('a')
    
    # Social media patterns
    social_patterns = ['facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 'tiktok']
    
    for link in all_links:
        href = link.get_attribute('href')
        text = link.inner_text().strip()
        rel = link.get_attribute('rel')
        target = link.get_attribute('target')
        
        if not href:
            continue
            
        # Convert to absolute URL
        if not href.startswith(('http://', 'https://', 'mailto:', 'tel:')):
            href = urljoin(base_url, href)
        
        link_info = {
            'url': href,
            'text': text[:100] if text else None,
            'rel': rel,
            'target': target,
            'is_visible': link.is_visible()
        }
        
        # Categorize
        if href.startswith(('mailto:', 'tel:')):
            links['external'].append(link_info)
        elif base_url.split('/')[2] in href:
            links['internal'].append(link_info)
        else:
            links['external'].append(link_info)
        
        # Check social
        for pattern in social_patterns:
            if pattern in href.lower():
                links['social'].append(link_info)
                break
        
        # Check navigation
        parent = link.evaluate('''
            element => {
                const nav = element.closest('nav');
                const header = element.closest('header');
                const footer = element.closest('footer');
                return !!(nav || header || footer);
            }
        ''')
        if parent:
            links['navigation'].append(link_info)
    
    # Save links
    filename = os.path.join(folder_path, "links.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(links, f, indent=2, ensure_ascii=False)
    
    print(f"🔗 Found {len(all_links)} links, saved to {filename}")
    print(f"   - Internal: {len(links['internal'])}")
    print(f"   - External: {len(links['external'])}")
    print(f"   - Social: {len(links['social'])}")
    
    return links


def get_user_input():
    """Legacy function - kept for compatibility"""
    urls = get_multiple_urls()
    return urls[0] if urls else ""


def get_multiple_urls():
    """Get multiple URLs from user"""
    print("\n" + "="*60)
    print("ENTER URLS TO SCRAPE")
    print("="*60)
    print("Enter one URL per line.")
    print("Press Enter twice (empty line) when done.\n")
    
    urls = []
    count = 1
    
    while True:
        url = input(f"URL {count}: ").strip()
        
        if not url:  # Empty line means done
            if not urls:  # If no URLs entered yet
                print(" Please enter at least one URL.")
                continue
            break
            
        # Basic URL validation
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'https://' + url
            print(f"   Added https:// prefix: {url}")
        
        urls.append(url)
        count += 1
    
    print(f"\n Added {len(urls)} URLs to process.")
    return urls


# ===== MAIN RUN FUNCTION =====

def run(playwright, url, take_screenshot, url_index=None, total_urls=None):
    """Main function to run the scraper with proper rendering"""
    
    # Show progress if multiple URLs
    if url_index is not None and total_urls is not None:
        print(f"\n Progress: URL {url_index}/{total_urls}")
    
    # Launch browser with better rendering settings
    browser = playwright.chromium.launch(
        headless=False, 
        slow_mo=2000,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--window-position=0,0',  # Position at top-left
            '--window-size=1024,768'   # Smaller window size
        ]
    )
    
    # Create context with smaller viewport
    context = browser.new_context(
        viewport={'width': 1024, 'height': 600},  # Smaller viewport
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='en-US',
        timezone_id='Asia/Kolkata',
        color_scheme='light',
        reduced_motion='no-preference',
        forced_colors='none'
    )
    
    # Minimal automation removal
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    page = context.new_page()
    
    # Set default timeout
    page.set_default_timeout(60000)
    
    # Go to URL
    print(f"\n Navigating to: {url}")
    page.goto(url)
    time.sleep(3)
    
    # Handle authentication
    if not auth_handler.handle_authentication(page, context, url, timeout=60):
        print(" Could not authenticate. Exiting...")
        browser.close()
        return
    
    print(" Authentication successful! Proceeding with scraping...")
    
    # Wait for page to be fully rendered
    page.wait_for_load_state("domcontentloaded")
    time.sleep(4)
    
    # Create main data folder for this URL
    data_folder = __create_page_folder(page.title())
    print(f"📁 Created data folder: {data_folder}/")
    
    # Save page text
    __save_page_text(page, "body", data_folder)
    time.sleep(1)
    
    # Now scrape and save everything to the folder
    if take_screenshot:
        screenshot_folder = __capture_multiple_screenshots(page)
        print(f"📁 Screenshots saved in folder: {screenshot_folder}")
    
    headlines_found = __scrape_headlines(page, data_folder)
    time.sleep(1)
    
    images = __scrape_images(page, url, data_folder)
    time.sleep(1)
    
    metadata_found = __scrape_metadata(page, data_folder)
    time.sleep(1)
    
    links_found = __scrape_all_links(page, url, data_folder)
    
    # Save a summary file
    summary = {
        'url': url,
        'title': page.title(),
        'headlines_count': len(headlines_found),
        'images_count': len(images),
        'links_count': len(links_found['internal']) + len(links_found['external']),
        'data_folder': data_folder,
        'screenshot_folder': screenshot_folder if take_screenshot else None
    }
    
    summary_path = os.path.join(data_folder, "summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Summary saved to {summary_path}")
    
    context.close()
    browser.close()