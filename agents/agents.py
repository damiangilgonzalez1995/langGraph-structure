from states.states import AgentGraphState
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter
from utils.utils import *
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic
import datetime as dt
from utils.setup_logging import setup_logging
import logging
import json

# Configurar los logs
setup_logging()

# Obtener un logger para el módulo actual
logger = logging.getLogger(__name__)


class Agent:

    def __init__(self, state: AgentGraphState):
        self.state = state

        data_config = get_config_file()

        self.server_models = data_config["SERVER_MODELS"]
        self.models = data_config["MODELS"]
        self.origen = data_config["ORIGENES"]
        self.model_embedding = data_config["MODEL_EMBEDDING"]


    def get_llm(self, agent):

        if self.server_models[agent] == "claude":
            return ChatAnthropic(model=self.models[agent], max_tokens_to_sample=2000)
        elif self.server_models[agent] == "groq":
            return ChatGroq(model=self.models[agent])
        
    def update_state(self, key, value):
        self.state = {**self.state, key: value}
        
    def check_state(self):
        if self.state["state_ok_ko"] == False:
            logger.error("Previous step went wrong")
            return False
        
        logger.info("Previous step was correct")
        return True
      

class FilterAgent(Agent):
    def invoke(self, prompt):
        
        class correctFormat(BaseModel):
            """The correct format to give the final response"""

            quien_vende: str = Field(description="consulta enfocada a quien_vende")
            a_quien_vende: str = Field(description="consulta enfocada a_quien_vende")
            como_se_vende: str = Field(description="consulta enfocada como_se_vende")
            magnitudes: str = Field(description="consulta enfocada a magnitudes")
            cuando: str = Field(description="cuando")
            que_vende: str = Field(description="consulta enfocada a que_vende")

        logger.info("FilterAgent started")

        try:
            input = self.state["input"]

            prompt = ChatPromptTemplate.from_template(template=prompt)
            
            llm = self.get_llm("FILTER_AGENT")

            setup = {"USER_QUERY": itemgetter("USER_QUERY") | RunnablePassthrough()}

            query_maker = setup | prompt | llm.with_structured_output(correctFormat)
                        
            response = query_maker.invoke({"USER_QUERY": input})

            self.update_state("input_filter", response) 
            self.update_state("state_ok_ko", True) 

            logger.info("FilterAgent finished successfully")

        except Exception as e:
            logger.error(f"Error in FilterAgent: {str(e)}")
            self.update_state("query", {}) 
            self.update_state("state_ok_ko", False) 
            return self.state


        return self.state
    

        

class RetrieverAgent(Agent):

    def invoke(self, db):

        """
        Para entenderlo mejor en un futuro:
        La query que se debe de hacer es la misma pero con filtros distintos. Vamos a obtener el embedding del input del usuario.
        Acto seguido, vamosa  crear un objeto que hará la consulta en la base de datos, teniendo como input el vector y los filtros.
        Usamos una funcion lambda para crear el objeto teniendo como parámetro de entrada el vector. Esto se hace porque queremos ejecutar las
        distintas consultas en paralelo.

        En la parte de creación del objeto que harála consulta a la base de datos, vamos a guardarlo en un diccionario, según el filtro/origen.

        {'cuando': <function __main__.<dictcomp>.<lambda>(embeddings, k='cuando')>,
        'quien_vende': <function __main__.<dictcomp>.<lambda>(embeddings, k='quien_vende')>,
        'a_quien_vende': <function __main__.<dictcomp>.<lambda>(embeddings, k='a_quien_vende')>,
        'como_se_vende': <function __main__.<dictcomp>.<lambda>(embeddings, k='como_se_vende')>,
        'mangnitudes': <function __main__.<dictcomp>.<lambda>(embeddings, k='mangnitudes')>,
        'que_vende': <function __main__.<dictcomp>.<lambda>(embeddings, k='que_vende')>}
        """
        if self.check_state():

            logger.info("RetrieverAgent started")
            
            try:
                input_filter = self.state["input_filter"]

                if input_filter is None:

                    input_filter = {
                            "quien_vende":  self.state["input"],
                            "a_quien_vende":  self.state["input"],
                            "como_se_vende":  self.state["input"],
                            "magnitudes":  self.state["input"],
                            "cuando":  self.state["input"],
                            "que_vende":  self.state["input"]
                        }

                retriever_results = {}

                retriever_results = db.retriever_fields(input=input_filter)

                if "error" in list(retriever_results.keys()):
                    error = retriever_results["error"]

                    logger.error(f"Error in RetrieverAgent: {str(error)}")
                    self.update_state("relevant_fields", "") 
                    self.update_state("state_ok_ko", False) 
                    return self.state  
                             
                else: 
                    fields_str = str(retriever_results["retriever"])

                    self.update_state("relevant_fields", fields_str) 
                    self.update_state("state_ok_ko", True) 

                    logger.info("RetrieverAgent finishing successfully")

            except Exception as e:
                logger.error(f"Error in RetrieverAgent: {str(e)}")
                self.update_state("relevant_fields", "") 
                self.update_state("state_ok_ko", False) 

                return self.state

        
        return self.state 
    
    def _create_list(self, elem: dict):
        return {"name": elem.metadata["name"],
                "type": elem.metadata["type"],
                "description": elem.page_content}



class QueryMakerAgent(Agent):

    def invoke(self, prompt):
        """
        Use this tool when you need to transform the user request into a functional query for elastic search.
        To use this tool, only insert the text that is relevant to the query.
        """

        if self.check_state():

            class correctFormat(BaseModel):
                """The correct format to give the final query"""

                query: str = Field(description="the query in JSON format")

            logger.info("QueryMakerAgent started")

            try:
                input = self.state["input"]
                relevant_fields = self.state["relevant_fields"]


                prompt = ChatPromptTemplate.from_template(template=prompt)
                
                llm = self.get_llm("QUERY_MAKER_AGENT")

                setup = {"USER_QUERY": itemgetter("USER_QUERY") | RunnablePassthrough(), 
                        "AVAILABLE_FIELDS": itemgetter("AVAILABLE_FIELDS") | RunnablePassthrough(),
                        "DATE": itemgetter("DATE") | RunnablePassthrough()}

                query_maker = setup | prompt | llm.with_structured_output(correctFormat)
                            
                response = query_maker.invoke({"USER_QUERY": input, "AVAILABLE_FIELDS": relevant_fields, "DATE": str(dt.date.today())})

                json_data  = json.loads(response['query'])

                if "query" in json_data and "size" in json_data:
                    if json_data["size"] <= 0:
                        json_data["size"] = 10

                response['query'] = json.dumps(json_data, indent=4)

                self.update_state("query", response) 
                self.update_state("state_ok_ko", True) 

                logger.info("QueryMakerAgent finished successfully")

            except Exception as e:
                logger.error(f"Error in QueryMakerAgent: {str(e)}")
                self.update_state("query", {}) 
                self.update_state("state_ok_ko", False) 
                return self.state


        return self.state
