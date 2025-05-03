#!/usr/bin/env python3
"""
Tor Dork Search - An OSINT tool for searching DuckDuckGo via Tor using dorks
"""

import requests
import random
import time
import argparse
import os
from tqdm import tqdm, trange
from urllib.parse import unquote, urlparse
import socks
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set, Optional
import re

# Constants
TOR_PROXY = "socks5h://127.0.0.1:9050"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
MAX_RETRIES = 3
MIN_DELAY = 5
MAX_DELAY = 10
MAX_WORKERS = 3
REQUEST_TIMEOUT = 30

def check_tor_connection() -> bool:
    """Check if Tor connection is working properly"""
    try:
        session = get_session()
        response = session.get("https://check.torproject.org/api/ip", timeout=REQUEST_TIMEOUT)
        return '"IsTor":true' in response.text
    except Exception:
        return False

def configure_tor_proxy() -> None:
    """Configure system to use Tor SOCKS5 proxy"""
    try:
        socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
        socket.socket = socks.socksocket
    except Exception as e:
        raise ConnectionError(f"Failed to configure Tor proxy: {e}")

def get_session() -> requests.Session:
    """Create and configure a requests session with Tor"""
    session = requests.Session()
    session.proxies = {'http': TOR_PROXY, 'https': TOR_PROXY}
    session.headers.update({
        'User-Agent': DEFAULT_USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    session.timeout = REQUEST_TIMEOUT
    return session

def search_duckduckgo(query: str, session: requests.Session) -> Optional[str]:
    """Search DuckDuckGo using Tor"""
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    
    try:
        response = session.get(url)
        response.raise_for_status()
        
        # Check for CAPTCHA page
        if "https://duckduckgo.com/sorry" in response.url:
            tqdm.write(f"⚠️ CAPTCHA encountered for query: {query}")
            return None
            
        return response.text
    except requests.exceptions.RequestException as e:
        tqdm.write(f"⚠️ Error searching '{query[:50]}...': {str(e)}")
        return None

def extract_links(page_content: str) -> List[str]:
    """Extract unique HTTP/HTTPS links from page content"""
    links = set()
    
    if not page_content:
        return []
    
    # Multiple extraction methods to handle different HTML structures
    # Method 1: Standard result links
    for match in re.finditer(r'<a.*?href="(.*?)".*?>', page_content):
        url = unquote(match.group(1))
        if url.startswith('http') and 'duckduckgo.com' not in url:
            links.add(url)
    
    # Method 2: Redirect URLs
    for match in re.finditer(r'uddg=(.*?)&', page_content):
        url = unquote(match.group(1))
        if url.startswith('http'):
            links.add(url)
    
    # Method 3: Result URL class
    for match in re.finditer(r'class="result__url".*?href="(.*?)"', page_content):
        url = unquote(match.group(1))
        if url.startswith('http'):
            links.add(url)
    
    return sorted(links)

def process_dork(dork: str, session: requests.Session) -> Set[str]:
    """Process a single dork with retries and delays"""
    links = set()
    
    for attempt in range(MAX_RETRIES):
        try:
            content = search_duckduckgo(dork, session)
            if content:
                new_links = extract_links(content)
                if new_links:
                    links.update(new_links)
                    break
                
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        except Exception as e:
            tqdm.write(f"⚠️ Error processing '{dork[:50]}...': {e}")
            time.sleep(random.uniform(MIN_DELAY * 2, MAX_DELAY * 2))
    
    if not links:
        tqdm.write(f"❌ Failed after {MAX_RETRIES} attempts: {dork[:50]}...")
    else:
        tqdm.write(f"✔️ Found {len(links)} links for: {dork[:50]}...")
    
    return links

def main():
    """Main function to parse arguments and execute the search"""
    parser = argparse.ArgumentParser(description='OSINT Search with Tor using Dorks')
    parser.add_argument('-d', '--dorks', required=True, 
                       help='Path to dorks file (.txt)')
    parser.add_argument('-o', '--output', default="tor_dork_results.txt",
                       help='Output file path')
    parser.add_argument('-j', '--workers', type=int, default=MAX_WORKERS,
                       help='Number of concurrent workers')
    args = parser.parse_args()

    # Validate input file
    if not os.path.isfile(args.dorks):
        print(f"❌ Dorks file not found: {args.dorks}")
        return

    # Read dorks
    try:
        with open(args.dorks, 'r', encoding='utf-8') as f:
            dorks = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"❌ Error reading dorks file: {e}")
        return

    if not dorks:
        print("❌ No dorks found in the file.")
        return

    # Configure Tor and verify connection
    try:
        configure_tor_proxy()
        if not check_tor_connection():
            print("❌ Tor connection check failed. Is Tor running?")
            return
        print("✔️ Tor connection verified")
    except ConnectionError as e:
        print(f"❌ {e}")
        return

    # Process dorks
    all_links = set()
    session = get_session()

    print(f"\n🔍 Starting search for {len(dorks)} dorks with {args.workers} workers...\n")
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_dork, dork, session): dork 
            for dork in dorks
        }

        for future in tqdm(as_completed(futures), total=len(dorks), desc="Processing"):
            try:
                links = future.result()
                all_links.update(links)
            except Exception as e:
                tqdm.write(f"⚠️ Unexpected error: {e}")

    # Save results
    try:
        with open(args.output, 'w', encoding='utf-8') as f_out:
            for link in sorted(all_links):
                f_out.write(f"{link}\n")
        
        print(f"\n✅ Search completed. Found {len(all_links)} unique links")
        print(f"📄 Results saved to: {os.path.abspath(args.output)}")
        
        if not all_links:
            print("\nℹ️  No links were found. Possible reasons:")
            print("- Tor connection issues")
            print("- DuckDuckGo is blocking requests")
            print("- The dorks didn't match any results")
            print("- Try increasing delays between requests")
    except Exception as e:
        print(f"❌ Failed to save results: {e}")

if __name__ == "__main__":
    main()
