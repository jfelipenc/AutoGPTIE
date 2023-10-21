from ..registry import ability
from ai_memory import get_step_output_from_stepid
from forge.sdk import (
    ForgeLogger, 
    chat_completion_request, 
    PromptEngine
)
import json

LOG = ForgeLogger(__name__)

@ability(
    name="generate_graph",
    description="Generates the code for a plotly.js graph from a task given by the user and data retrieved in previous steps. Use when requested to graph anything.",
    parameters=[
        {
            "name": "data",
            "description": "Data to be used in the graph.",
            "type": "dict",
            "required": True,
        }
    ],
    output_type="str"
)
async def generate_graph(agent, task_id: str, data: dict) -> str:
    task = await agent.db.get_task(task_id)
    
    prompt_engine = PromptEngine("agents")
    
    system_format = prompt_engine.load_prompt("grapher-system-format")
    
    task_kwargs = {
        "task": task.input,
        "data": data
    }
    
    task_prompt = prompt_engine.load_prompt("grapher-task-step", **task_kwargs)
    
    messages = [
        {"role": "system", "content": system_format},
        {"role": "user", "content": await agent.check_and_trim_message(task_prompt)}
    ]
    
    try:
        chat_completion_kwargs = {
            "messages": messages,
            "model": "gpt-3.5-turbo",
        }
    
        chat_response = await chat_completion_request(**chat_completion_kwargs)
        generated_code = json.loads(chat_response["choices"][0]["message"]["content"])
        LOG.info(f"Generated code: {generated_code}")
        return generated_code
    except Exception as e:
        LOG.error(f"Error generating graph: {e}")
        return ""