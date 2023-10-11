import json
import pprint
import datetime
import time
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
    """
    The goal of the Forge is to take care of the boilerplate code so you can focus on
    agent design.

    There is a great paper surveying the agent landscape: https://arxiv.org/abs/2308.11432
    Which I would highly recommend reading as it will help you understand the possabilities.

    Here is a summary of the key components of an agent:

    Anatomy of an agent:
         - Profile
         - Memory
         - Planning
         - Action

    Profile:

    Agents typically perform a task by assuming specific roles. For example, a teacher,
    a coder, a planner etc. In using the profile in the llm prompt it has been shown to
    improve the quality of the output. https://arxiv.org/abs/2305.14688

    Additionally baed on the profile selected, the agent could be configured to use a
    different llm. The possabilities are endless and the profile can be selected selected
    dynamically based on the task at hand.

    Memory:

    Memory is critical for the agent to acculmulate experiences, self-evolve, and behave
    in a more consistent, reasonable, and effective manner. There are many approaches to
    memory. However, some thoughts: there is long term and short term or working memory.
    You may want different approaches for each. There has also been work exploring the
    idea of memory reflection, which is the ability to assess its memories and re-evaluate
    them. For example, condensting short term memories into long term memories.

    Planning:

    When humans face a complex task, they first break it down into simple subtasks and then
    solve each subtask one by one. The planning module empowers LLM-based agents with the ability
    to think and plan for solving complex tasks, which makes the agent more comprehensive,
    powerful, and reliable. The two key methods to consider are: Planning with feedback and planning
    without feedback.

    Action:

    Actions translate the agents decisions into specific outcomes. For example, if the agent
    decides to write a file, the action would be to write the file. There are many approaches you
    could implement actions.

    The Forge has a basic module for each of these areas. However, you are free to implement your own.
    This is just a starting point.
    """

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

        We are hooking into function to add a custom log message. Though you can do anything you
        want here.
        
        # version 2023-10-04
        Adding planning LLM call to outline task steps beforehand. 
        Hoping to reduce strain and erros in step execution.
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
                step_id=step_id
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
        LOG.info(f"Executing step #{step_inc+1} with body: {substep_request}")
        
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
            step_additional_input=str(substep.additional_input),
            task_id=task_id,
            created_at=substep.created_at.isoformat("T")+"Z"
        )
        
        # creates prompt for response format
        system_prompt = prompt_engine.load_prompt("system-format")
        
        # creates prompt for retrieving important information
        retrieval_prompt = f"""
            Given the task input below, provide suitable information from previous steps:
            
            {substep.input}
        """
        
        previous_step_output = json.dumps(await self.vectordb.search_memory_gen(
                prompt=retrieval_prompt,
                class_name="StepOutput"
                )
            )
        LOG.info(f"Previous step output summarized by the LLM: {previous_step_output}")
        
        # specify task parameters
        task_kwargs = {
            "task": substep.input,
            "additional_input": substep.additional_input,
            "previous_step_output": previous_step_output,
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
        LOG.info(f"Answer for this step #{step_inc+1}: {answer}")
        
        # extracts the ability required to execute the step
        try:
            # selects ability to run
            ability = answer["ability"]
            
            # run the ability and get the output
            output = await self.abilities.run_ability(
                task_id, ability["name"], **ability["args"]
            )
            output = {'output': output}
            
            # captures the Speak part as output or whole answer
            #try:
            #    substep.output = answer["thoughts"]["speak"]
            #except Exception as e:
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
        """
        For a tutorial on how to add your own logic please see the offical tutorial series:
        https://aiedge.medium.com/autogpt-forge-e3de53cc58ec

        The agent protocol, which is the core of the Forge, works by creating a task and then
        executing steps for that task. This method is called when the agent is asked to execute
        a step.

        The task that is created contains an input string, for the bechmarks this is the task
        the agent has been asked to solve and additional input, which is a dictionary and
        could contain anything.

        If you want to get the task use:

        ```
        task = await self.db.get_task(task_id)
        ```

        The step request body is essentailly the same as the task request and contains an input
        string, for the bechmarks this is the task the agent has been asked to solve and
        additional input, which is a dictionary and could contain anything.

        You need to implement logic that will take in this step input and output the completed step
        as a step object. You can do everything in a single step or you can break it down into
        multiple steps. Returning a request to continue in the step output, the user can then decide
        if they want the agent to continue or not.
        """
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
        
        # creating steps
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
    