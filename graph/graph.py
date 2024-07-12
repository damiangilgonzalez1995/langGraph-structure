from langgraph.graph import StateGraph
from states.states import AgentGraphState
import json
from utils.setup_logging import setup_logging
import logging
from agents.agents import (
    RetrieverAgent,
    QueryMakerAgent,
    FilterAgent
)
from prompts.prompts import (
    prompt_query_maker,
    prompt_filter
)

# Configurar los logs
setup_logging()

# Obtener un logger para el módulo actual
logger = logging.getLogger(__name__)

class GraphMaker():

    def __init__(self) -> None:
        self.graph = None
        self.workflow = None

    def create_graph(self, db: dict):
        try:
            graph = StateGraph(AgentGraphState)

            graph.add_node("filter_agent", 
                        lambda state: FilterAgent(state=state
                                                        ).invoke(prompt=prompt_filter))

            graph.add_node("retriever_agent", 
                        lambda state: RetrieverAgent(state=state
                                                        ).invoke(db=db)
                            )
            
            graph.add_node("query_maker_agent",
                            lambda state: QueryMakerAgent(state=state).invoke(prompt=prompt_query_maker))

            graph.add_edge('filter_agent', 'retriever_agent')
            graph.add_edge('retriever_agent', 'query_maker_agent')

            graph.set_entry_point("filter_agent")
            # graph.set_entry_point("retriever_agent")

            graph.set_finish_point("query_maker_agent")

            self.graph = graph

            workflow = graph.compile()

            self.create_imagen_graph(workflow)

            self.workflow = workflow

            logger.info("Graph and workflow created successfully")

            return graph, workflow
        
        except Exception as e:
            logger.error(f"Error creating graph and workflow: {e}")
            return None, None

    def create_workflow(self, db: dict):
        graph, workflow = self.create_graph(db=db)
        return graph, workflow

    def call_graph(self, input_user: str):
        json_query = {}
        try:
            response = self.workflow.invoke({
                "input": input_user,
                "input_cleaned": "",
                "relevant_fields": "",
                "query": "",
            })

        except Exception as e:
            logger.error(f"Error invoking the workflow: {e}")
            return None

        try:
            json_query = {"query": json.loads(response.get("query", {}).get("query", "{}"))}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

        logger.info("Workflow invoked and JSON query created successfully")

        return json_query
    
    def create_imagen_graph(self, workflow):
        output_path = './data/graph_image.png'

        try:
            # Genera la imagen
            image_data = workflow.get_graph(xray=True).draw_mermaid_png()
            
            # Guarda la imagen en el path especificado
            with open(output_path, 'wb') as f:
                f.write(image_data)

        except Exception as e:
            print(f"Se produjo un error: {e}")
            # Manejo opcional de la excepción
            pass
