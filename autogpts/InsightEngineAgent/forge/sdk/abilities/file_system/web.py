import requests
import os
from bs4 import BeautifulSoup

from forge.sdk import ForgeLogger
from ..registry import ability
from .files import write_file

LOG = ForgeLogger(__name__)

def get_search_api(name: str = 'Brave'):
    engines = {'Brave': 'BRAVE_SEARCH_API'}
    try:
        return os.getenv(engines[name])
    except:
        raise f"Could not find API key for {name}, please check your environment variables!"

@ability(
    name="fetch_webpage",
    description="Retrieves the content of a webpage",
    parameters=[
        {
            "name": "url",
            "description": "Webpage URL",
            "type": "string",
            "required": True
        }
    ],
    output_type="string"
)
async def fetch_webpage(agent, task_id: str, url: str) -> str:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content)
    content = soup.get_text()
    return content

@ability(
    name="fetch_write_webpage",
    description="Retrieves the content of a URL and saves to a .txt file. Requires the URL.",
    parameters=[
        {
            "name": "url",
            "description": "Webpage URL",
            "type": "string",
            "required": True
        },
        {
            "name": "filepath",
            "description": "Path to output TXT file",
            "type": "string",
            "required": True
        }
    ],
    output_type="None"
)
async def fetch_write_webpage(agent, task_id: str, url: str, filepath: str):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content)
    content = soup.get_text()
    await write_file(agent, task_id, filepath, content)
    
@ability(
    name="search_query",
    description="Search the web for a specific query and returns a list of urls.",
    parameters=[
        {
            "name": "search_query",
            "description": "Desired query to search for using search engine",
            "type": "string",
            "required": True
        },
        {
            "name": "search_engine",
            "description": "Search engine to be used for retrieving the results. Available engines: Brave.",
            "type": "string",
            "required": False
        }
    ],
    output_type="list"
)
async def search_query(agent, task_id: str, search_query: str, search_engine: str = "Brave"):
    # Engines specifications
    engines = {
        "Brave": {
            "endpoint": "https://api.search.brave.com/res/v1/web/search",
            "headers": {
                #'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'X-Subscription-Token': get_search_api('Brave')
            }
        }
    }
    
    # Parameters
    params = {
        'q': search_query,
        'count': 3
    }
    
    # Parameters for request
    try:
        url = engines[search_engine]["endpoint"]
        headers = engines[search_engine]["headers"]
    except:
        print(f"Failed on retrieving engine {search_engine}, reverting to Brave...")
        url = engines["Brave"]["endpoint"]
        headers = engines["Brave"]["headers"]
    
    # Retrieving results from the api
    response = requests.get(url, headers=headers, params=params)
    json_response = response.json()
    print(f"GET responses for {search_query}")
    
    # Retrieves URLs
    urls = [result['url'] for result in json_response['web']['results']]
    
    return urls