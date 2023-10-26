from typing import List

from forge.sdk import ForgeLogger
from ..registry import ability

LOG = ForgeLogger(__name__)

@ability(
    name="search_memory_gen",
    description="Searches the memory of the agent's objects with a prompt using Generative AI",
    parameters=[
        {
            "name": "prompt",
            "type": "string",
            "description": "The prompt for requesting information, summarizing or reframing content",
            "required": True,
        },
        {
            "name": "concept",
            "type": "string",
            "description": "The concept to group the objects by",
            "required": True,
        },
        {
            "name": "class_name",
            "type": "string",
            "description": "The class name of the objects to search for",
            "required": True,
        }
    ],
    output_type="list[dict]"
)
async def search_memory_gen(agent, task_id: str, prompt: str, concept: str, class_name: str) -> List[dict]:
    LOG.info(f"Searching memory for {prompt}...")
    search_results = await agent.ai_memory.search_memory_gen(prompt)
    LOG.info(f"Search results: {search_results}")
    return search_results["data"]["Get"][class_name]