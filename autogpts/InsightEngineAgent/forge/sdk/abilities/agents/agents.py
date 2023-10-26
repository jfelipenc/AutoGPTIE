import subprocess
from ..registry import ability
from forge.sdk import (
    ForgeLogger, 
    chat_completion_request, 
    PromptEngine
)

LOG = ForgeLogger(__name__)

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
    last_output = agent.vectordb.get_step_output_from_stepid(step_id)
    
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

@ability(
    name="run_python_env",
    description="Opens a Python environment and runs code from a list of strings",
    parameters=[
        {
            "name": "command_list",
            "description": "List of ordered python commands to run on the environment",
            "type": "list",
            "required": True
        }
    ],
    output_type="string"
)
async def run_python_code(agent, task_id: str, command_list: []) -> str:
    process = subprocess.Popen(['python'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    
    output_list = []
    for cmd in command_list:
        output = process.communicate(input=cmd)[0]
        output_list.append(output)
    
    output = b' '.join(output_list)
    return output.decode()
    