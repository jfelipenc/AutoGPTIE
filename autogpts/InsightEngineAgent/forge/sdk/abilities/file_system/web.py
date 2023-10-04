import requests
from bs4 import BeautifulSoup

from forge.sdk import ForgeLogger
from ..registry import ability
from .files import write_file

LOG = ForgeLogger(__name__)

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
    response = requests.get(url)
    return response.text

@ability(
    name="fetch_write_webpage",
    description="Retrieves the content of a webpage and saves to a .txt file",
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
    response = requests.get(url)
    soup = BeautifulSoup(response.content)
    content = soup.get_text()
    await write_file(agent, task_id, filepath, content)