import os
from dotenv import load_dotenv  # Import dotenv
from gql import Client
from gql.transport.requests import RequestsHTTPTransport
from keycloak import KeycloakOpenID

# Load environment variables from .env file
load_dotenv()

def get_client():
    try:
        DEURL = os.getenv("DEURL")
        username = os.getenv("USERNAME")
        password = os.getenv("PASSWORD")

        if not all([DEURL, username, password]):
            raise EnvironmentError("Missing required env variables")

        keycloak_url = f"https://auth-{DEURL}/auth/"
        api_url = f"https://api-{DEURL}/graphql"

        keycloak_openid = KeycloakOpenID(
            server_url=keycloak_url, client_id="dash", realm_name="dash"
        )

        token = keycloak_openid.token(username, password)["access_token"]
        transport = RequestsHTTPTransport(
            url=api_url,
            headers={
                "Content-type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            use_json=True,
        )
        return Client(transport=transport)
    except Exception as e:
        print(f"Error getting client: {str(e)}")
        raise EnvironmentError("Missing required env variables")
