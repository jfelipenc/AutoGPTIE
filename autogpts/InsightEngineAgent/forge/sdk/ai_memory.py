import os
import weaviate
import datetime

from .forge_log import ForgeLogger

LOG = ForgeLogger(__name__)

# generative-openai is used for RAG
# text2vec-openai is used for vectorization

SYSTEM_SCHEMAS = [
    {
        "class": "Task",
        "properties": [
            {
                "name": "taskId",
                "dataType": ["uuid"],
            },
            {
                "name": "taskInput",
                "dataType": ["text"],
            },
            {
                "name": "taskAdditionalInput",
                "dataType": ["text"],
            },
            {
                "name": "createdAt",
                "dataType": ["date"],
            },
            {
                "name": "successful",
                "dataType": ["boolean"],
                "description": "Whether the task was successful or not"
            },
            {
                "name": "n_retry",
                "dataType": ["int"],
                "description": "Number of times the task was retried"
            }
        ],
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {},
            "generative-openai": {}
        }
    },
    {
        "class": "Step",
        "properties": [
            {
                "name": "stepId",
                "dataType": ["uuid"],
            },
            {
                "name": "stepName",
                "dataType": ["text"],
            },
            {
                "name": "stepInput",
                "dataType": ["text"],
            },
            {
                "name": "stepAdditionalInput",
                "dataType": ["text"],
            },
            {
                "name": "taskId",
                "dataType": ["text"],
            },
            {
                "name": "createdAt",
                "dataType": ["date"],
            },
            {
                "name": "ability_chosen",
                "dataType": ["text"],
                "description": "The ability chosen to execute the step"
            },
            {
                "name": "ability_parameters",
                "dataType": ["text"],
                "description": "The parameters passed to the ability"
            },
            {
                "name": "successful",
                "dataType": ["boolean"],
                "description": "Whether the step was successful or not"
            },
            {
                "name": "retry_sequence",
                "dataType": ["int"],
                "description": "If more than one retry, this number reflects in which retry sequence the step was executed"
            }
        ],
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {},
            "generative-openai": {}
        }
    },
    {
        "class": "StepOutput",
        "properties": [
            {
                "name": "stepOutputId",
                "dataType": ["uuid"],
            },
            {
                "name": "outputThought",
                "dataType": ["text[]"],
            },
            {
                "name": "outputValue",
                "dataType": ["text[]"],
            },
            {
                "name": "outputType",
                "dataType": ["text"],
            },
            {
                "name": "stepId",
                "dataType": ["text"],
            },
            {
                "name": "createdAt",
                "dataType": ["date"],
            },
        ],
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {},
            "generative-openai": {}
        }
    },
    {
        "class": "Artifacts",
        "properties": [
            {
                "name": "artifactId",
                "dataType": ["uuid"],
            },
            {
                "name": "artifactName",
                "dataType": ["text"],
            },
            {
                "name": "artifactDescription",
                "dataType": ["text"],
            },
            {
                "name": "artifactPath",
                "dataType": ["text"],
            },
            {
                "name": "createdAt",
                "dataType": ["date"],
            }
        ],
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {}
        }
    },
]

class AgentVectorDB:
    def __init__(self, API_KEY_ENV: str = "WEAVIATE_API_KEY",
                 url: str = "https://insight-engine-vdb-0m9lhl20.weaviate.network") -> None:
        super().__init__()
        WEAVIATE_API_KEY = os.getenv(API_KEY_ENV)
        auth_config = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
        self.client = weaviate.Client(
            url=url,
            auth_client_secret=auth_config,
            additional_headers={
                "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")
            }
        )
        self.create_system_schemas()

    def create_system_schemas(self):
        schemas = self.client.schema.get()
        for schema in SYSTEM_SCHEMAS:
            if not self.client.schema.contains(schema):
                try:
                    print(f"Creating new schema {schema['class']}...")
                    self.client.schema.create_class(schema)
                except Exception as e:
                    LOG.warning(f"Failed creating system schemas due to {e}")
    
    async def create_task(self, task_id: str, task_name: str = "", task_input: str = "", task_additional_input: str = "", created_at: str = ""):
        task = {
            "class": "Task",
            "properties": {
                "taskId": task_id,
                "taskName": task_name,
                "taskInput": task_input,
                "taskAdditionalInput": task_additional_input,
                "createdAt": created_at
            }
        }
        self.client.data_object.create(class_name=task["class"], 
                                       data_object=task["properties"])
        
    async def create_step(self, step_id: str, step_name: str, step_input: str, step_additional_input: str, task_id: str, created_at: str):
        step = {
            "class": "Step",
            "properties": {
                "stepId": step_id,
                
                "stepName": step_name,
                "stepInput": step_input,
                "stepAdditionalInput": step_additional_input,
                "taskId": task_id,
                "createdAt": created_at
            }
        }
        self.client.data_object.create(class_name=step["class"], 
                                       data_object=step["properties"])
    
    async def update_step_additional_input(self, step_id: str, step_additional_input: str):
        step = {
            "class": "Step",
            "properties": {
                "stepAdditionalInput": step_additional_input
            }
        }
        self.client.data_object.update(class_name=step["class"], uuid=step_id,
                                       data_object=step["properties"])
    
    async def create_step_output(self, step_output_id: str, output_thought: str, output_value: str, output_type: str, step_id: str):
        step_output = {
            "class": "StepOutput",
            "properties": {
                "stepOutputId": step_output_id,
                "outputThought": output_thought,
                "outputValue": output_value,
                "outputType": output_type,
                "stepId": step_id,
                "createdAt": datetime.datetime.now().isoformat("T")+"Z"
            }
        }
        self.client.data_object.create(class_name=step_output["class"], 
                                       data_object=step_output["properties"])
        
    async def create_artifact(self, artifact_id: str, artifact_name: str, artifact_description: str, artifact_path: str, created_at: str):
        artifact = {
            "class": "Artifacts",
            "properties": {
                "artifactId": artifact_id,
                "artifactName": artifact_name,
                "artifactDescription": artifact_description,
                "artifactPath": artifact_path,
                "createdAt": created_at
            }
        }
        self.client.data_object.create(class_name=artifact["class"], 
                                       data_object=artifact["properties"])
        
    async def get_step_output(self, step_output_id: str):
        step_output = self.client.data_object.get(class_name="StepOutput", id=step_output_id)
        return step_output
    
    async def get_output_with_stepid(self, step_id: str):
        graphql = """
        {
            Get {
                StepOutput(
                sort: {path: ["createdAt"], order: desc}
                limit: 1
                where: {path: ["stepId"], operator: Equal, valueString: "%s"}
                ) {
                stepOutputId
                stepId
                outputThought
                outputValue
                createdAt
                }
            }
        }
        """
        response = self.client.query.raw(graphql % step_id)
        return response
    
    async def get_all_steps_from_task(self, task_id: str):
        graphql = """{
                Get {
                    Step(where: {taskId: {eq: "%s"}}) {
                        stepId,
                        stepName,
                        stepInput,
                        stepAdditionalInput,
                        createdAt
                }
            }"""
        response = self.client.query.raw(graphql % task_id)
        return response

    async def search_step_output(self, search_query: str):
        response = (
            self.client.query
            .get("StepOutput", ["outputThought", "outputValue"])
            .with_near_text({
                "concepts": [search_query],
            })
            .with_limit(3)
            .with_additional(["distance"])
            .do()
            )
        
        return response

    async def search_memory_gen(self, prompt: str, class_name: str = "StepOutput"):
        response = (
            self.client.query
            .get(class_name, ["outputThought", "outputValue"])
            .with_generate(grouped_task=prompt)
            #.with_near_text({
            #    "concepts": [concept],
            #})
            .with_limit(5)
        ).do()
        
        return response