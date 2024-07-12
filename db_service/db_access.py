import os
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from utils.utils import get_config_file
from utils.setup_logging import setup_logging
from prompts.prompts import *
import logging
import requests
from pinecone import Pinecone as pinecone_client
from pinecone import ServerlessSpec
from langchain_core.runnables import RunnableParallel
import time
from db_service.api_fields import ApiFields

# Configurar los logs
setup_logging()

# Obtener un logger para el módulo actual
logger = logging.getLogger(__name__)

class VectorDB():

    def __init__(self):
        self.data_yaml = get_config_file()
        self.embedding_model = OpenAIEmbeddings(model=self.data_yaml["MODEL_EMBEDDING"])
        self.k = self.data_yaml["k"]
        self.index = None
        self.documents = None
        self.retriever = None
        self.fields_origen = None
        self.pinecone = None


        self.PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
        self.PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]
        self.PINECONE_COLLECTION_NAME = os.environ["PINECONE_COLLECTION_NAME"]
        self.OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

        logger.info("Initializing Pinecone client...")
        self.pinecone = pinecone_client(api_key=self.PINECONE_API_KEY, environment=os.environ["ENVIRONMENT"])

    def get_json_fields(self):
        try:
            client = ApiFields()
            data = client.execute()
            
            if data:
                logging.info("Data retrieval successful")
            else:
                logging.warning("No data returned from the API")
            
            return data
        
        except requests.RequestException as e:
            logging.error(f'API request error: {e.response.status_code}')
            logging.error(f'Error details: {e.response.text}')
            return None
        except Exception as e:
            logging.error(f'An unexpected error occurred: {str(e)}')
            return None


    def create_retriever(self):
        try:
            # Inicializando el índice de Pinecone
            self.index = self.pinecone.Index(self.PINECONE_INDEX_NAME)
            logger.info(f"Index '{self.PINECONE_INDEX_NAME}' initialized successfully")

            # Describiendo el índice y obteniendo las namespaces
            self.fields_origen = list(self.index.describe_index_stats()["namespaces"].keys())
            logger.info(f"Namespaces retrieved successfully: {self.fields_origen}")

            # Creando el retriever
            self.retriever = PineconeVectorStore(self.index, self.embedding_model)
            logger.info("Retriever created successfully")
            return self.retriever

        except Exception as e:
            logger.error(f"Error creating retriever: {e}")
            logger.error("You must make the post request to update the vector database")
            return None


    def update_retriever(self):
        try:
            self.empty_index()
            documents_dict = self.create_documents()
            self.retriever = self.insert_documents_in_index(documents_dict)
            logger.info("Retriever created successfully")
            return {
                "status": "success",
                "message": "Retriever created successfully",
                "documents_count": len(documents_dict)  # Por ejemplo, cantidad de documentos insertados
            }
        except Exception as e:
            logger.error(f"Error creating retriever: {e}")
            return {
                "status": "error",
                "message": f"Error creating retriever: {e}"
            }

    def retriever_fields(self, input: dict):

        try:
            # if (self.retriever is not None) and (self.fields_origen is not None):
            embeddings_dict = self.__embedding_input(input)
            
            obj_db_query_dict = {key: (lambda em , key_param=key: self.retriever.similarity_search_by_vector_with_score(
                        embedding=em[key_param],
                        namespace=key_param,
                        k=self.k)) for key in self.fields_origen}
            
            search_vector_chain = RunnableParallel(obj_db_query_dict)
            docs_dict = search_vector_chain.invoke(input=embeddings_dict)
            retriever_results = {key: [self.__create_list(elem) for elem in docs_dict[key]] for key in docs_dict.keys()}
            logger.info("Fields retrieved successfully")
            return {"retriever": retriever_results}
        except Exception as e:
            logger.error(f"Error retrieving fields: {e}")
            return {"error": str(e)}

    def __create_list(self, elem: dict):
        try:
            return {"name": elem[0].metadata["name"],
                    "type": elem[0].metadata["type"],
                    "description": elem[0].page_content}
        except Exception as e:
            logger.error(f"Error creating list from element: {e}")
            return elem[0]
        
    def __embedding_input(self, input: dict):

        try:

            embeddings_model = self.embedding_model     

            values = [value for value in input.values()]

            embeddings_vector = embeddings_model.embed_documents(values)

            embedding_dict = {key: embedding for key, embedding in zip(input.keys(), embeddings_vector)}
            logger.info("Embeddings successfully created")

            return embedding_dict
        except Exception as e:
            logger.error(f"Error creating embeddings: {e}")
            return None

    def insert_documents_in_index(self, documents: dict):
        try:
            fields_origen_list = []
            for key in documents.keys():
                logger.info(f"Inserting documents into index for namespace: {key}")
                fields_origen_list.append(key)
                docs = documents[key]
                retreivers = PineconeVectorStore.from_documents(documents=docs,
                                                               embedding=self.embedding_model,
                                                               index_name=self.PINECONE_INDEX_NAME,
                                                               namespace=key)
            self.fields_origen = fields_origen_list
            logger.info("Documents inserted into index successfully")
            return retreivers
        except Exception as e:
            logger.error(f"Error inserting documents into index: {e}")
            return None
        
    def _get_index(self):

        try:
            
            index = None
            
            existing_indexes = [index_info["name"] for index_info in self.pinecone.list_indexes()]
            logger.info(f"Existing indexes: {existing_indexes}")

            if type(existing_indexes) is not list:
                existing_indexes = [existing_indexes]

            if self.PINECONE_INDEX_NAME not in existing_indexes:
                logger.info(f"Index '{self.PINECONE_INDEX_NAME}' does not exist. Creating index...")
                self.pinecone.create_index(
                    name=self.PINECONE_INDEX_NAME,
                    dimension=1536,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
                
                while not self.pinecone.describe_index(self.PINECONE_INDEX_NAME).status["ready"]:
                    logger.info("Index not ready yet, waiting 1 second...")
                    time.sleep(1)
                logger.info("Index is ready.")
                
            index = self.pinecone.Index(self.PINECONE_INDEX_NAME)

            self.index = index

        except Exception as e:
            logger.error(f"Error initializing Pinecone index: {e}")


    def empty_index(self):
        try:
            self._get_index()

            list_namespace = list(self.index.describe_index_stats()["namespaces"].keys())

            if list_namespace:
                for namespace in list_namespace:
                    logger.info(f"Clearing namespace: {namespace}")
                    self.index.delete(delete_all=True, namespace=namespace)
            
            logger.info(f"Index '{self.PINECONE_INDEX_NAME}' retrieved successfully.")
            return self.index
        
        except Exception as e:
            logger.error(f"Error initializing Pinecone index: {e}")
            return None
        
    def __create_description(self, name, description, synonyms, possible_values):
        description_test = f"nombre: {name} | descripcion: {description}"

        # if len(synonyms) > 2:
        #     description_test += f"sinonimos: {synonyms}"
        # if len(possible_values) > 2:
        #     description_test += f"posibles valores: {possible_values[0:20]}"

        return description_test

    def create_documents(self):
        documents_dict = {}
        try:
            json_fields = self.get_json_fields()
            if json_fields:
                for key in json_fields.keys():
                    documents = []
                    for elem in json_fields[key]:
                        try:
                            name = elem["name"]
                            description = elem["description"]
                            synonyms = elem["synonyms"]
                            possible_values = elem["possible_values"]
                        
                            page_content = self.__create_description(name, description, synonyms, possible_values)
                                                            
                            documents.append(Document(page_content=page_content, 
                                                        metadata={
                                                            "name": elem["name"],
                                                            "type": elem["type"],
                                                            "synonyms": elem["synonyms"],
                                                            "origin": key
                                                        }))
                        except KeyError as ke:
                            logger.error(f"Missing key in element {elem}: {ke}")
                        except Exception as inner_e:
                            logger.error(f"Error processing element {elem}: {inner_e}")
                    
                    documents_dict[key] = documents
            logger.info("Documents created successfully")
        except requests.RequestException as re:
            logger.error(f"API request error while retrieving JSON fields: {re.response.status_code} - {re.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error creating documents: {e}")
        
        return documents_dict