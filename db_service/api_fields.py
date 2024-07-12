import requests
import logging
from utils.setup_logging import setup_logging
import os


# Configurar los logs
setup_logging()

# Obtener un logger para el módulo actual
logger = logging.getLogger(__name__)

class ApiFields:
    def __init__(self):

        self.url_auth = os.environ["URL_AUTH"]
        self.url_endpoint = os.environ["URL_FIELDS"]
 
        self.headers_auth = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        self.headers_endpoint = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        self.data_auth = {
            "login":  os.environ["LOGIN"],
            "password":  os.environ["PASS"]
        }
        self.session = requests.Session()


    def authenticate(self):
        try:
            auth_response = self.session.post(self.url_auth, headers=self.headers_auth, json=self.data_auth)
            auth_response.raise_for_status()
            logger.info('Authentication successful')
            cookies = self.session.cookies.get_dict()
            logger.debug(f'Session cookies: {cookies}')
            return True
        except requests.RequestException as e:
            logger.error(f'Authentication error: {e.response.status_code}')
            logger.error(f'Error details: {e.response.text}')
            return False

    def get_data(self):
        endpoint_data = {
            "filter": {
                "condition": "AND",
                "rules": []
            },
            "vfl": "",
            "posStart": 0,
            "count": 200
        }
        try:
            endpoint_response = self.session.post(self.url_endpoint, headers=self.headers_endpoint, json=endpoint_data)
            endpoint_response.raise_for_status()
            logger.info('Second endpoint call successful')
            logger.debug(f'Response: {endpoint_response.json()}')
            return self.process_data(endpoint_response.json()["rows"])
        except requests.RequestException as e:
            logger.error(f'Second endpoint call error: {e.response.status_code}')
            logger.error(f'Error details: {e.response.text}')
            return None
        

    def process_data(self, data):
        grouped_by_type = {}
        for item in data:
            type = item.get('tipo')
            if type not in grouped_by_type:
                grouped_by_type[type] = []
            grouped_by_type[type].append({
                'name': item.get('name'),
                'type': item.get('type'),
                'description': item.get('description'),
                'synonyms': item.get('sinonimos'),
                'possible_values': item.get('possible_values'),
            })
        return grouped_by_type

    def execute(self):
        if self.authenticate():
            return self.get_data()
        return None


