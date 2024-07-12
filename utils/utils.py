import yaml
import os
from dotenv import load_dotenv

def get_config_file():
    try:
            with open('config/config.yaml', 'r') as file:
                data = yaml.load(file, Loader=yaml.FullLoader)
                return data
    except FileNotFoundError:
        print("Error: El archivo 'config/config.yaml' no se encontró.")
    except yaml.YAMLError as exc:
        print(f"Error al analizar el archivo YAML: {exc}")
    except Exception as exc:
        print(f"Se produjo un error inesperado: {exc}")


    return {}



def load_env_variables():
    load_dotenv()
    env_variables = {
        "OPENAI_API_KEY": os.getenv('OPENAI_API_KEY'),
        "ANTHROPIC_API_KEY": os.getenv('ANTHROPIC_API_KEY'),
        "LANGCHAIN_API_KEY": os.getenv('LANGCHAIN_API_KEY'),
        "LANGCHAIN_TRACING_V2": os.getenv('LANGCHAIN_TRACING_V2'),
        "LANGCHAIN_PROJECT": os.getenv('LANGCHAIN_PROJECT'),
        "URL_AUTH": os.getenv("URL_AUTH"),
        "URL_FIELDS": os.getenv("URL_FIELDS"),
        "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY"),
        "PINECONE_COLLECTION_NAME": os.getenv("PINECONE_COLLECTION_NAME"),
        "PINECONE_INDEX_NAME": os.getenv("PINECONE_INDEX_NAME")    
    }



    return env_variables