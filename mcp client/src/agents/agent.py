import os
import boto3
from langchain.agents import create_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain.agents.middleware import SummarizationMiddleware
from langchain.messages import HumanMessage, SystemMessage
from langchain_aws import ChatBedrock
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.prompts import load_mcp_prompt
from langchain_mcp_adapters.resources import load_mcp_resources
from langchain_mcp_adapters.tools import load_mcp_tools
from agents.prompt import SystemPrompt
from src.models.custom_app_exepction import CustomAppException
from utils.errors.error_codes import ErrorCode
from utils.errors.error_log import log_error
from utils.errors.http_status import HttpStatusCode
from models.request_dto import ChatbotResponse
from setting import config
from langchain.agents.structured_output import ToolStrategy


MCP_SERVER_URL = config.mcp_server_url

DB_URI =   (
            f"postgresql://{config.db_username}:"
            f"{config.db_password}@"
            f"{config.db_host}:"
            f"{config.db_port}/"
            f"{config.db_name}"
        )


class Agent:
    def __init__(self):
        self.prompt = SystemPrompt()
    def mcp_client(self):
        client = MultiServerMCPClient(
            {
                "mcp-client": {
                    "transport" : "streamable_http",
                    "url": MCP_SERVER_URL,
                }
            }
        )
        print("mcp_client")
        return client
    def get_bedrock_client(self):

        client = boto3.client(
            service_name="bedrock-runtime",
            region_name=config.region,
            aws_access_key_id =os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        print("bedrock")
        return client

    def get_llm(self,max_tokens=5000, temperature=0.2):

        llm = ChatBedrock(
            client=self.get_bedrock_client(),
            model_id=os.getenv("MODEL_ID"),
            provider="amazon",
            model_kwargs={
                "maxTokenCount": max_tokens,
                "temperature": temperature,
            },
        )
        print("llm")
        return llm
    async def load_mcp_components(self, session, user_query):
        print("tools is called")
        tools = await load_mcp_tools(session) 
        print("tools is loaded")
        print(type(user_query))
        query = user_query.lower()
        print("query is called")
        diet_keywords=["diet","low calorie","vegan","healthy","sugar","protein"]
        if any(word in query for word in diet_keywords):
            selected_prompt = "diet_planning"
        else:
            selected_prompt = "explain_menu"
        print(selected_prompt)
 
        prompt_messages = []
   
        try:
            loaded_prompt = await load_mcp_prompt(session, selected_prompt, arguments = {"user_query": user_query})
            if isinstance(loaded_prompt, list):
                print("loaded_prompt")
                prompt_messages.extend(loaded_prompt)
            else:
                prompt_messages.append(loaded_prompt)
        except Exception as e:
            print("Error loading prompt:",str(e))
        resources = await load_mcp_resources(session)
        resource_context = ""
        for resource in resources:
            try:
                text = resource.as_bytes().decode("utf-8", errors="replace")
                uri = resource.metadata.get("uri", "resource")
                resource_context += f"\n[{uri}]\n{text}\n"
            except Exception as e:
                continue
        if resource_context:
            prompt_messages.append(SystemMessage(content=f"Here are the available resources:\n{resource_context}"))
        return tools, prompt_messages
    
    
    async def create_agents(self,tools,llm, system_prompt,prompt,user_query,customer_uuid):
        print("checkpointer")
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        # create tables first time

            await checkpointer.setup()
            print(" checkpointer CONNETCED")
            agent = create_agent(
                model=llm,
                tools=tools,
               
                checkpointer=checkpointer,
               
                middleware = [
                    SummarizationMiddleware(
                        model = self.get_llm(max_tokens= 150, temperature=0.3),
                        trigger = ("tokens",5),
                        keep = ("messages",2),
                      
                    )
                ], 
                response_format=ToolStrategy(
                    ChatbotResponse
            )
            )
            print("agent created")
            messages = [SystemMessage(content=system_prompt)]+prompt + [HumanMessage(content = user_query)]
            print(messages)
            result = await agent.ainvoke(
                    {"messages":messages},
                    {"configurable": {"thread_id": str(customer_uuid)}}
                )
            print("agent Invoked")
            # return result
            return result["structured_response"]


    async def chatbot_agent(self,user_query,customer_uuid):
        try:
            mcp_client = self.mcp_client()
            client = self.get_bedrock_client()
            llm = self.get_llm()
            async with mcp_client.session("mcp-client") as session:
                tools,prompt = await self.load_mcp_components(session,user_query)
                system_prompt = self.prompt.get_system_prompt()
                result = await self.create_agents(tools,llm,system_prompt,prompt,user_query,customer_uuid)
                return result
            
        except Exception as e:
            log_error("agent.py","chatbot_agent",str(e))
            raise CustomAppException(
                message=f"Agent error: {str(e)}",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                status_code=HttpStatusCode.INTERNAL_SERVER_ERROR,
                 
            )
