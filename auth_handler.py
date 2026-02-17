from playwright.sync_api import sync_playwright
import json
import time
import os
import re
from urllib.parse import urlparse

class AuthHandler:
    """Universal authentication handler for any website"""
    
    def __init__(self, cookie_dir="cookies"):
        self.cookie_dir = cookie_dir
        os.makedirs(cookie_dir, exist_ok=True)
    
    def _get_domain_key(self, url):
        """Extract domain from URL to use as cookie filename"""
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').split(':')[0]
        return domain
    
    def _get_cookie_file(self, url):
        """Get cookie file path for a given URL"""
        domain = self._get_domain_key(url)
        safe_domain = re.sub(r'[^\w\.-]', '_', domain)
        return os.path.join(self.cookie_dir, f"{safe_domain}_cookies.json")
    
    def load_cookies(self, context, url):
        """Load saved cookies for a specific site"""
        cookie_file = self._get_cookie_file(url)
        
        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, 'r') as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)
                print(f"Loaded {len(cookies)} cookies from {cookie_file}")
                return True
            except Exception as e:
                print(f"Error loading cookies: {e}")
        return False
    
    def save_cookies(self, context, url):
        """Save cookies for a specific site"""
        cookie_file = self._get_cookie_file(url)
        cookies = context.cookies()
        
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"\n Saved {len(cookies)} cookies to {cookie_file}")
        return cookies
    
    def is_login_required(self, page):
        """
        Universal login detection for any website
        Returns True if login/signup is detected, False if page seems accessible
        Handles navigation errors gracefully
        """
        
        try:
            # SPECIAL CASE: Instagram login page detection
            try:
                instagram_login = page.query_selector('text="Sign up for Instagram"')
                if instagram_login:
                    print(" Instagram signup prompt detected")
                    return True
            except Exception:
                # Page navigated during check, continue
                pass
            
            # Check for login form (username + password fields)
            try:
                username_field = page.query_selector('input[name="username"]')
                password_field = page.query_selector('input[type="password"]')
                
                if username_field and password_field:
                    print(" Login form detected (username + password fields)")
                    return True
            except Exception:
                pass
            
            # Check page URL for login patterns
            try:
                url_lower = page.url.lower()
                url_login_indicators = ['login', 'signin', 'sign-in', 'signup', 'sign-up', 'register', 'auth', 'accounts']
                for indicator in url_login_indicators:
                    if indicator in url_lower:
                        print(f" Login indicator in URL: {indicator}")
                        return True
            except Exception:
                pass
            
            # Check page title
            try:
                title = page.title().lower()
                title_indicators = ['login', 'sign in', 'sign up', 'register', 'log in']
                for indicator in title_indicators:
                    if indicator in title:
                        print(f" Login indicator in title: {indicator}")
                        return True
            except Exception:
                pass
            
            # Check for login buttons
            login_buttons = [
                'button:has-text("Log in")',
                'button:has-text("Sign in")',
                'button:has-text("Login")',
                'button:has-text("Log In")',
                'button:has-text("Sign In")',
                'a:has-text("Log in")',
                'a:has-text("Sign in")'
            ]
            
            for selector in login_buttons:
                try:
                    if page.query_selector(selector):
                        print(f"🔍 Login button detected: {selector}")
                        return True
                except Exception:
                    continue
            
            # Check for "Create new account" or similar
            try:
                signup_links = page.query_selector('a:has-text("Create new account")')
                if signup_links:
                    print(" Create new account link detected")
                    return True
            except Exception:
                pass
            
        except Exception as e:
            print(f" Navigation detected during login check: {e}")
            return True  # Assume login required if page is navigating
        
        return False
    
    def is_logged_in(self, page, original_url):
        """
        Check if we're actually logged in and on a content page
        Handles navigation errors gracefully
        """
        try:
            # First, if login is required, we're not logged in
            try:
                if self.is_login_required(page):
                    return False
            except Exception:
                # If we can't even check, assume not logged in
                return False
            
            # For Instagram specifically, check for profile elements
            if 'instagram.com' in original_url:
                profile_indicators = [
                    'header img[alt*="profile picture"]',
                    'section:has-text("posts")',
                    'section:has-text("followers")',
                    'article',
                    'div:has-text("Posts")',
                    'svg[aria-label="Home"]',
                    'svg[aria-label="Profile"]'
                ]
                
                for selector in profile_indicators:
                    try:
                        if page.query_selector(selector):
                            print(f" Found profile indicator: {selector}")
                            return True
                    except Exception:
                        continue
            
            # For Facebook specifically
            if 'facebook.com' in original_url:
                fb_indicators = [
                    'a[aria-label="Home"]',
                    'a[aria-label="Profile"]',
                    'div[role="navigation"]',
                    'svg[aria-label="Notifications"]',
                    'div:has-text("Friends")',
                    'div[aria-label="Your profile"]',
                    'a[href*="/friends/"]'
                ]
                
                for selector in fb_indicators:
                    try:
                        if page.query_selector(selector):
                            print(f"🔍 Found Facebook logged-in indicator: {selector}")
                            return True
                    except Exception:
                        continue
            
            # Generic check
            try:
                return not self.is_login_required(page)
            except Exception:
                return False
                
        except Exception as e:
            print(f" Error checking logged-in status: {e}")
            return False
    
    def handle_authentication(self, page, context, original_url, timeout=60):
        """
        Handle authentication for any website
        Returns True if authenticated successfully, False otherwise
        """
        
        print(f"\n Checking authentication for: {original_url}")
        
        # First, try to load existing cookies
        cookies_loaded = self.load_cookies(context, original_url)
        
        # Go to the original URL
        print(f" Navigating to: {original_url}")
        page.goto(original_url)
        time.sleep(5)  # Increased wait time
        
        # Check if we're already logged in and on content page
        try:
            if self.is_logged_in(page, original_url):
                print(" Already logged in! No authentication needed.")
                return True
        except Exception as e:
            print(f" Navigation during initial check: {e}")
            # Continue to login flow
        
        # Login is required
        print("\n" + "="*60)
        print(" LOGIN REQUIRED")
        print("="*60)
        
        if cookies_loaded:
            print(" Saved cookies didn't work. They may have expired.")
            print("   Need to log in again to refresh cookies.")
        
        print(f"\n Please log in manually in the browser window.")
        print(f"⏳ You have {timeout} seconds to complete the login...")
        print(f"\n TIPS:")
        print("   • After logging in, you may be redirected to the home page")
        print("   • The script will automatically navigate back to your target page")
        print("   • Don't close the browser window during login")
        print("\n" + "="*60)
        
        # Countdown timer with periodic login check
        logged_in = False
        for i in range(timeout, 0, -1):
            # Check every 3 seconds if login was successful
            if i % 3 == 0:
                try:
                    if self.is_logged_in(page, original_url):
                        print(f"\n Login detected at {timeout - i} seconds!")
                        logged_in = True
                        break
                except Exception as e:
                    # Page probably navigated, continue waiting
                    pass
                
                if i % 9 == 0:  # Every 9 seconds, remind user
                    print(f"\n Still waiting for login... {i} seconds remaining")
            
            print(f"   Waiting... {i:2d} seconds remaining", end='\r')
            time.sleep(1)
        
        print("\n")
        
        if logged_in:
            # We're logged in, but might be on home page, not target page
            print(f"Navigating to target page: {original_url}")
            
            # Small delay to let everything settle
            time.sleep(2)
            
            try:
                page.goto(original_url)
                time.sleep(5)
            except Exception as e:
                print(f"Navigation error: {e}")
                time.sleep(3)
                # Try one more time
                try:
                    page.goto(original_url)
                    time.sleep(5)
                except:
                    pass
            
            # Final verification with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if self.is_logged_in(page, original_url):
                        print("Successfully reached target page!")
                        
                        # Save the new cookies
                        self.save_cookies(context, original_url)
                        print(" New cookies saved for future sessions!")
                        return True
                except Exception as e:
                    print(f" Verification attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(2)
                    try:
                        page.goto(original_url)
                        time.sleep(3)
                    except:
                        pass
            
            print(" Could not verify login on target page.")
            return False
        else:
            print("Login timeout. Authentication failed.")
            return False