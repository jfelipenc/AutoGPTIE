import requests

from ..registry import ability

@ability(
    name="fetch_webpage",
    description="Retrieves the content of a webpage as HTML code",
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