from ..registry import ability
from ai_memory import get_step_output_from_stepid
from forge.sdk import (
    ForgeLogger, 
    chat_completion_request, 
    PromptEngine
)

LOG = ForgeLogger(__name__)

@ability(
    name="build_sql_query",
    description="Calls an Agent to build a SQL query to retrieve input requested information",
    parameters=[
        {
            "name": "step_input",
            "description": "Input request from step",
            "type": "string",
            "required": True
        }
    ],
    output_type="string"
)
def build_sql_query(agent, task_id: str, step_input: str) -> str:
    #TODO: load prompt format for SQL generation, query vector database for schema of available databases
    #TODO: fill prompt, make chat completion request, return SQL query
    
    pass

@ability(
    name="insight_agent",
    description="Calls an Agent to analyze data from last executed step and return insights in text form",
    parameters=[
        {
            "name": "step_id",
            "description": "Data to analyze",
            "type": "string",
            "required": True
        }
    ],
    output_type="string"
)
async def insight_agent(agent, task_id: str, step_id: str) -> str:
    last_output = get_step_output_from_stepid(step_id)
    
    prompt_engine = PromptEngine("agents")
    
    task_kwargs = {
        "last_output": last_output,
    }
    
    task_prompt = prompt_engine.load_prompt("insight-agent", **task_kwargs)
    
    system_prompt = prompt_engine.load_prompt("system-format")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_prompt}
    ]
    
    answer = await chat_completion_request(**messages)
    return answer["choices"][0]["message"]["content"]