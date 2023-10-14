import json
import pprint
import datetime
import time
import re
import uuid

import tiktoken

from forge.sdk import (
    Agent,
    AgentDB,
    AgentVectorDB,
    Step,
    StepRequestBody,
    Workspace,
    ForgeLogger,
    Task,
    TaskRequestBody,
    PromptEngine,
    chat_completion_request,
)

LOG = ForgeLogger(__name__)


class ForgeAgent(Agent):
    def __init__(self, database: AgentDB, vectordb: AgentVectorDB, workspace: Workspace):
        """
        The database is used to store tasks, steps and artifact metadata. The workspace is used to
        store artifacts. The workspace is a directory on the file system.

        Feel free to create subclasses of the database and workspace to implement your own storage
        """
        super().__init__(database, vectordb, workspace)

    async def create_task(self, task_request: TaskRequestBody) -> Task:
        """
        The agent protocol, which is the core of the Forge, works by creating a task and then
        executing steps for that task. This method is called when the agent is asked to create
        a task.
        """
        task = await super().create_task(task_request)
        LOG.info(
            f"📦 Task created: {task.task_id} input: {task.input[:40]}{'...' if len(task.input) > 40 else ''}"
        )
        return task
    
    async def check_and_trim_message(self, message: str) -> str:
        enc = tiktoken.encoding_for_model('gpt-3.5-turbo')
        num_tokens = len(enc.encode(message))
        if num_tokens >= 4097:
            excess = num_tokens - 4097
            while num_tokens >= 4097:
                split_by = int(excess / 3)
                message = message[:split_by]
        return message
    
    async def make_chat_completion(self, messages: list) -> dict:
        answer = {}
        try:
            # define the parameters for chat completion request
            chat_completion_kwargs = {
                "messages": messages,
                "model": "gpt-3.5-turbo",
            }
            # make chat completion request and parse response
            chat_response = await chat_completion_request(**chat_completion_kwargs)
            answer = json.loads(chat_response["choices"][0]["message"]["content"])
            # Logs the answer
            LOG.info(f"Answer: {pprint.pformat(answer)}")
        except json.JSONDecodeError as e:
            # Handling JSON Decoding errors
            LOG.error(f"""Unable to decode chat response: {chat_response}
                      failed with error {e}""")
            answer = None
        except Exception as e:
            # Handling other exceptions
            LOG.error(f"Unable to generate chat response: {e}")
            answer = None
            
        return answer
    
    async def adding_substep_output(self,
                                    step_output_thought: dict,
                                    step_output_value: dict,
                                    step_id: str
                                    ):
        
        output_values = [str(value) for key, value in step_output_value.items()]
        output_thoughts = [str(value) for key, value in step_output_thought.items()]
        LOG.info("Creating output artifact on vector database...")
        try:
            await self.vectordb.create_step_output(
                step_output_id=str(uuid.uuid4()),
                output_thought=output_thoughts,
                output_value=output_values,
                step_id=step_id,
            )
        except Exception as e:
            LOG.warning(f"Failed creating output artifact on vector database due to {e}")
    
    async def execute_substep(self, 
                              task_id: str,
                              step_inc: int,
                              is_last: bool,
                              prompt_engine: PromptEngine, 
                              substep_request: StepRequestBody,
                              error_info: str) -> Step:
        LOG.info(f"""
                 Executing step #{step_inc+1}:
                    input: {substep_request.input}
                    additional_input: {substep_request.additional_input}
                {'Last execution error:'+ error_info if error_info != '' else ''}
                 """)

        if error_info != "":
            substep_request.additional_input["error_info"] = error_info
        
        # Create new step in database
        substep = await self.db.create_step(
            task_id=task_id, input=substep_request, is_last=is_last
        )
        # Create step in vector database
        await self.vectordb.create_step(
            step_id=substep.step_id,
            step_name=substep.name,
            step_input=substep.input,
            step_additional_input=str(substep_request.additional_input),
            task_id=task_id,
            created_at=substep.created_at.isoformat("T")+"Z"
        )
        LOG.info(f"STEP CREATED: {substep}")
        
        # creates prompt for response format
        system_prompt = prompt_engine.load_prompt("system-format")
        
        # specify task parameters
        task_kwargs = {
            "task": substep.input,
            "additional_input": substep_request.additional_input,
            "error_info": error_info if error_info != "" else "",
            "abilities": self.abilities.list_abilities_for_prompt(),
        }
        
        # load task prompt with parameters
        task_prompt = prompt_engine.load_prompt("task-step", **task_kwargs)
        
        # messages list
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": await self.check_and_trim_message(task_prompt)}
        ]
        
        # Chat completion request
        answer = await self.make_chat_completion(messages)
        if answer == None:
            answer = await self.make_chat_completion(messages)
        
        # extracts the ability required to execute the step
        try:
            # selects ability to run
            ability = answer["ability"]
            
            # run the ability and get the output
            output = await self.abilities.run_ability(
                task_id, ability["name"], **ability["args"]
            )
            output = {'output': output}

            # update the step with the output of answer
            substep.output = answer
                
            LOG.info(f"Finished executing step #{step_inc+1}.")
            
            # Creating object in database for step output
            await self.adding_substep_output(
                step_output_thought=substep.output,
                step_output_value=output,
                step_id=substep.step_id
            )
            error_info = ""
            return substep
        except Exception as e:
            error_info = str(e)
            return error_info
    
    async def execute_step(self, task_id: str, step_request: StepRequestBody) -> Step:
        # Get task to access task_input
        task = await self.db.get_task(task_id)
        
        # loads the prompt engine with gpt-3.5-turbo templates
        prompt_engine = PromptEngine("gpt-3.5-turbo")
        
        # planner response format
        planner_format = prompt_engine.load_prompt('plan-system-format')
        # instructions format
        task_plan_kwargs = {
            "date": str(datetime.date.today()),
            "task": task.input,
            "abilities": self.abilities.list_abilities_for_prompt()
        }
        task_plan = prompt_engine.load_prompt('task-plan-step', **task_plan_kwargs)
        messages = [
            {"role": "system", "content": planner_format},
            {"role": "user", "content": task_plan}
        ]
        
        # Creating steps from LLM planning agent
        plan_answer = await self.make_chat_completion(messages)
        planned_steps = plan_answer["plan"]
        
        LOG.info(f"ORIGINAL STEP REQUEST BODY: {step_request}")
        
        # ==== STEP EXECUTION ====
        for i, dict_step_request in enumerate(planned_steps):
            successful = False
            n_exec = 0
            error_info = ""
            
            while not successful and n_exec < 3:
                substep_request = StepRequestBody(
                    input=dict_step_request["input"],
                    additional_input=dict_step_request["additional_input"] if "additional_input" in list(dict_step_request.keys()) else None
                )
                is_last = True if i+1 == len(planned_steps) else False
                
                substep = await self.execute_substep(
                    task_id=task_id,
                    step_inc=i,
                    is_last=is_last,
                    prompt_engine=prompt_engine,
                    substep_request=substep_request,
                    error_info=error_info
                )
                if type(substep) == str:
                    error_info = substep
                    n_exec += 1
                else:
                    successful = True
            
            if n_exec == 3 and not successful:
                LOG.error(f"Failed execution of step {i+1}. Error information: {error_info}.\n")
                return substep
            
        if is_last:
            LOG.info(f"Finished execution of task: {task_id}.")
        return substep
    