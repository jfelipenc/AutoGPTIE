import json
import pprint
import datetime

from forge.sdk import (
    Agent,
    AgentDB,
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

    def __init__(self, database: AgentDB, workspace: Workspace):
        """
        The database is used to store tasks, steps and artifact metadata. The workspace is used to
        store artifacts. The workspace is a directory on the file system.

        Feel free to create subclasses of the database and workspace to implement your own storage
        """
        super().__init__(database, workspace)
        
    async def create_next_step(self, task_id: str, input, additional_input, is_last=True) -> Step: 
        step_request = await self.create_step_request(input, additional_input)
        
        next_step_exec = await self.execute_step(task_id, step_request)
        
        return next_step_exec
    
    async def create_step_request(self, input: str, additional_input: dict):
        if additional_input is None:
            additional_input = {}
            
        step_request = StepRequestBody()
        step_request.input = input
        step_request.additional_input = additional_input
        
        return step_request

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
        # loads prompt engine
        prompt_engine = PromptEngine("gpt-3.5-turbo")
        
        # creates prompt for response format
        system_prompt = prompt_engine.load_prompt('plan-system-format')
        
        # specify task-planning prompt parameters
        task_kwargs = {
            "date": str(datetime.date.today()),
            "task": task_request.input,
            "abilities": self.abilities.list_abilities_for_prompt()
        }
        
        # load task-planning prompt with params
        task_prompt = prompt_engine.load_prompt('task-plan-step', **task_kwargs)
        
        # messages list
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_prompt}
        ]
        
        # try getting planning from llm
        try:
            chat_completion_kwargs = {
                "messages": messages,
                "model": "gpt-3.5-turbo"
            }           
            # make chat completion request and parse response
            chat_response = await chat_completion_request(**chat_completion_kwargs) 
            answer = json.loads(chat_response["choices"][0]["message"]["content"])
            
            # Logging the answer as info for further analysis
            LOG.info(f"The planning agent answer for this task was: {pprint.pformat(answer)}")
        except json.JSONDecodeError as e:
            LOG.error(f"Unable to decode planning llm response f{chat_response} with error {e}")
        except Exception as e:
            LOG.error(f"Unable to get model's response due to {e}")
        
        # adding additional_input to task
        task_request.additional_input = answer['step']
        task = await super().create_task(task_request)
        LOG.info(
            f"📦 Task created: {task.task_id} input: {task.input[:40]}{'...' if len(task.input) > 40 else ''}"
        )
        
        return task

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
        
        # Get steps of task
        steps = await self.db.list_steps(task_id)
        
        # Gets step request additional inputs
        if steps[0] or len(steps[0]) > 1:
            try:
                LOG.info("Retrieving additional input from step.")
                additional_input = step_request.additional_input
            except Exception as e:
                LOG.error(f"Error processing additional input for step: {e}")
        else:
            LOG.info("First step in task identified. Importing task additional inputs...")
            additional_input = task.additional_input
        
        is_last = additional_input["is_last"] if "is_last" in additional_input.keys() else False
        
        # Create new step in database
        step = await self.db.create_step(
            task_id=task_id, input=step_request, additional_input=additional_input, is_last=is_last
        )
        
        # loads the prompt engine with gpt-3.5-turbo templates
        prompt_engine = PromptEngine("gpt-3.5-turbo")
        
        # creates prompt for response format
        system_prompt = prompt_engine.load_prompt("system-format")
        
        # specify task parameters
        task_kwargs = {
            "date": str(datetime.date.today()),
            "task": task.input,
            "step": step.input,
            "steps_outputs": step.output,#additional_input["output"] if "output" in list(additional_input.keys()) else "No output so far",
            "abilities": self.abilities.list_abilities_for_prompt(),
        }
        
        LOG.info(f"Steps outputs so far: {additional_input['output'] if 'output' in list(additional_input.keys()) else ''}")
        LOG.info(f"Step output: {step.output}")
        
        # load task prompt with parameters
        task_prompt = prompt_engine.load_prompt("task-step", **task_kwargs)
        
        LOG.info(f"Task prompt template: {task_prompt}")
        
        # messages list
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_prompt}
        ]
        
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
            LOG.info(pprint.pformat(answer))
        except json.JSONDecodeError as e:
            # Handling JSON Decoding errors
            LOG.error(f"""Unable to decode chat response: {chat_response}
                      failed with error {e}""")
        except Exception as e:
            # Handling other exceptions
            LOG.error(f"Unable to generate chat response: {e}")
            
        # extracts the ability required to execute the step
        ability = answer["ability"]
        # run the ability and get the output
        output = await self.abilities.run_ability(
            task_id, ability["name"], **ability["args"]
        )
        step.output = output#answer["thoughts"]["speak"]
        
        if not ability["is_last"]:
            # just testing
            LOG.info("Starting next step in chain!")
            next_step = await self.create_next_step(task_id, step.input, additional_input={"output": step.output})
        
        LOG.info(f"Finished execution with output: {step.output}")
        return step