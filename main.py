from db_service.db_access import VectorDB
from graph.graph import GraphMaker
import os
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import warnings
import uvicorn
from utils.setup_logging import setup_logging
from utils.utils import load_env_variables
import logging

# Configurar los logs
setup_logging()

# Obtener un logger para el módulo actual
logger = logging.getLogger(__name__)



warnings.filterwarnings("ignore", category=DeprecationWarning)


# Cargar variables de entorno
env_variables = load_env_variables()

# Configurar variables de entorno
os.environ.update(env_variables)

# Create Retreivers
db_obj = VectorDB()
db_obj.create_retriever()

print ("Creating graph and compiling workflow...")
graph_maker = GraphMaker()
graph_maker.create_workflow(db=db_obj)
print ("Graph and workflow created.")



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)


# Model Request
class requestInput(BaseModel):
    input_user: str
    type_query: str = "ES"


@app.post("/query_maker")
async def create_query(request_input: requestInput):

    input_user = request_input.input_user
    if request_input.type_query == "ES":
        response = graph_maker.call_graph(input_user=input_user)

        if not response: 
            logger.error("Error: In the process, something went wrong")
            raise HTTPException(status_code=400, detail="In the process, something went wrong")

    return response


@app.post("/update_vectordb")
async def update_vector_db():
    response = db_obj.update_retriever()

    if response["status"] == "error":
        logger.error(response["message"])
        raise HTTPException(status_code=400, detail=response["message"])

    return response



@app.get("/")
def root():
    return {"message": "API TEST"}

