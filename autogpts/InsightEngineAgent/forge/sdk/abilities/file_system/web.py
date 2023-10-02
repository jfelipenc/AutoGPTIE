import requests
from bs4 import BeautifulSoup

from ..registry import ability

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
    #soup = BeautifulSoup(response.content)
    #return soup.get_text()
    return response.text