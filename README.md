# Tor-Dork-Search
An OSINT tool for searching DuckDuckGo via Tor using search dorks.

## Features

- Anonymous searching through Tor network
- Multiple concurrent searches
- Multiple link extraction methods
- Automatic retries with delays
- CAPTCHA detection
- Progress tracking with tqdm

## Requirements

- Python 3.6+
- Tor service running locally
- Required Python packages (install via `requirements.txt`)

## Installation

1. Install Tor:
  
# For Debian/Ubuntu

sudo apt install tor
   
sudo systemctl start tor 

Clone this repository:

git clone https://github.com/Profanatic/tor-dork-search.git

cd tor-dork-search

Install dependencies:

pip3 install -r requirements.txt

Usage
Create a text file with your search dorks (one per line)

Run the script:

python3 tor_dork_search.py -d dorks.txt -o results.txt

Example

python3 tor_dork_search.py -d dorks.txt -o results.txt -j 5

Troubleshooting

If you get zero results:

Verify Tor is running (systemctl status tor)

Test Tor connection: torsocks curl https://check.torproject.org/api/ip

Try simpler dorks first

Increase delays between requests

Disclaimer
This tool is for educational and legitimate research purposes only. The developers are not responsible for any misuse of this software.
