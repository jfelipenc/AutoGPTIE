import os
import weaviate

from .forge_log import ForgeLogger

LOG = ForgeLogger(__name__)

SYSTEM_SCHEMAS = [
    {
        "class": "Task",
        "properties": [
            {
                "name": "taskId",
                "dataType": ["uuid"],
            },
            {
                "name": "taskName",
                "dataType": ["text"],
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
                "dataType": ["Task"],
            },
            {
                "name": "createdAt",
                "dataType": ["date"],
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
                "dataType": ["int"],
            },
            {
                "name": "outputThought",
                "dataType": ["text"],
            },
            {
                "name": "outputValue",
                "dataType": ["text"],
            },
            {
                "name": "stepId",
                "dataType": ["Step"],
            }
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
                "dataType": ["text"],
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
            "text2vec-openai": {},
            "generative-openai": {}
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
            if schema not in schemas["classes"]:
                try:
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
    
    async def create_step_output(self, step_output_id: str, output_thought: str, output_value: str, step_id: str):
        step_output = {
            "class": "StepOutput",
            "properties": {
                "stepOutputId": step_output_id,
                "outputThought": output_thought,
                "outputValue": output_value,
                "stepId": step_id
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