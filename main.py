import os
import subprocess
from datetime import datetime, timedelta
from gql import gql

from client import get_client
from queries import (
    GET_APP_BASIC_INFO,
    GET_APP_SERVICES,
    GET_ENV_VARIABLES,
    CREATE_APP_MUTATION,
    UPDATE_APP_MUTATION,
    CREATE_SERVICE_MUTATION,
)

# Protected environment variables that should not be overwritten
PROTECTED_ENV_KEYS = {
    "DASH_APP_NAME",
    "DASH_ROUTES_PATHNAME_PREFIX",
    "DASH_REQUESTS_PATHNAME_PREFIX",
    "DASH_PATH_ROUTING",
    "GUNICORN_CMD_ARGS",
    "DASH_LOGOUT_URL",
    "DASH_SECRET_KEY",
    "GIT_REV",
    "REDIS_URL",
    "DATABASE_URL",
}

DEURL = os.getenv("DEURL")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

old_client = get_client(DEURL, username, password)

DEURL = os.getenv("DEURL")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

new_client = get_client(DEURL, username, password)


def run_command(command, cwd=None):
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n❌ Command failed: {command}")
        print(result.stderr)
    else:
        lines = result.stdout.splitlines()
        cleaned_lines = [
            line for line in lines
            if not line.startswith("Building your app:") and
               not line.startswith("Deploying your app:") and
               not line.startswith("Pushing your app to Dash Enterprise:") and
               line.strip() != ""
        ]
        print(f"\n✅ Command succeeded: {command}")
        print("\n".join(cleaned_lines))

def fetch_all_apps():
    client = old_client
    all_apps = []
    last_created_at = None

    try:
        while True:
            filter_arg = {"filter": {"created_at": {"gt": last_created_at}}} if last_created_at else {}
            result = client.execute(gql(GET_APP_BASIC_INFO), variable_values=filter_arg)

            apps = result["apps"]["nodes"]
            all_apps.extend(apps)

            if not result["apps"]["pageInfo"]["hasNextPage"]:
                break

            last_created_at = apps[-1]["created_at"]
            dt = datetime.fromisoformat(last_created_at.replace("Z", "+00:00")) + timedelta(milliseconds=1)
            last_created_at = dt.isoformat().replace("+00:00", "Z")

        return [
            {
                "app_name": app["title"] or app["slug"],
                "author": app["author"]["username"],
                "slug": app["slug"],
                "created_at": datetime.fromisoformat(app["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d"),
            }
            for app in all_apps
        ]
    except Exception as e:
        print(f"Error fetching app basic info: {str(e)}")
        return []

def fetch_services_for_app(slug):

    client = old_client

    try:
        result = client.execute(gql(GET_APP_SERVICES), variable_values={"slug": slug})
        return result["app"]["services"]
    except Exception as e:
        print(f"Error fetching services for app {slug}: {str(e)}")
        return []

def fetch_env_vars_for_app(slug):

    client = old_client

    try:
        result = client.execute(gql(GET_ENV_VARIABLES), variable_values={"slug": slug})
        return result["app"]["environment_variables"]
    except Exception as e:
        print(f"Error fetching env vars for app {slug}: {str(e)}")
        return []

def filter_protected_env_vars(env_vars):
    return [
        {"key": var["key"], "value": var["value"], "description": var.get("description", "")}
        for var in env_vars if var["key"] not in PROTECTED_ENV_KEYS
    ]

def create_new_app(input_data):

    client = new_client
    try:
        result = client.execute(gql(CREATE_APP_MUTATION), variable_values={"input": {"app": input_data}})
        return result["createOneApp"]
    except Exception as e:
        print(f"Error creating app: {e}")
        return None

def update_app_env_vars(app_id, filtered_env_vars):

    client = new_client

    try:
        client.execute(gql(UPDATE_APP_MUTATION), variable_values={
            "input": {
                "id": app_id,
                "app": {"environment_variables": filtered_env_vars}
            }
        })
        print(f"✅ Updated env vars for app {app_id}")
    except Exception as e:
        print(f"Error updating env vars for app {app_id}: {e}")

def add_services_to_app(app_id, services):

    client = new_client

    for service in services:
        try:
            client.execute(gql(CREATE_SERVICE_MUTATION), variable_values={
                "input": {
                    "type": service["type"],
                    "name": service["name"],
                    "config": service["config"],
                    "app_id": app_id
                }
            })
            print(f"✅ Service {service['name']} added to app {app_id}")
        except Exception as e:
            print(f"Error adding service {service['name']} to app {app_id}: {e}")

def clone_and_deploy_repo(slug):
    old_de_url = os.getenv("DEURL", "https://tam.plotly.host")
    new_de_url = os.getenv("DEURL", "https://tam.plotly.host")
    repo_url = f"https://{old_de_url}/GIT/{slug}"
    clone_dir = f"./repos/{slug}-repo"
    new_slug = f"{slug}-copy"

    print(f"🔁 Cloning repo from {repo_url} into {clone_dir}")
    run_command(f"git clone {repo_url} {clone_dir}")

    print(f"🔁 Logging in to {new_de_url}")
    run_command(f"de --host {new_de_url} login")

    print(f"🚀 Deploying app to Dash Enterprise with slug '{new_slug}'")
    run_command(f"de deploy {clone_dir} --name {new_slug} -y")

def clone_app(app_data):
    slug = app_data["slug"]
    services = fetch_services_for_app(slug)
    env_vars = fetch_env_vars_for_app(slug)
    filtered_env_vars = filter_protected_env_vars(env_vars)

    new_slug = f"{slug}-copy"
    input_data = {
        "title": app_data["app_name"],
        "slug": new_slug,
        "description": f"Cloned app from {app_data['author']} on {datetime.now().isoformat()}",
        "visible_on_portal": True,
        "maintainer_name": app_data["author"],
        "maintainer_email": f"{app_data['author']}@example.com",
        "view_access": "PUBLIC",
        "edit_access": "PRIVATE",
        "app_type": "classic",
        "python_version": "3.10",
    }

    new_app = create_new_app(input_data)
    if not new_app:
        return

    update_app_env_vars(new_app["app_id"], filtered_env_vars)
    add_services_to_app(new_app["app_id"], services)
    clone_and_deploy_repo(slug)

def main():
    apps = fetch_all_apps()
    for app in apps:
        if app["slug"] == "dashauth-test":
            clone_app(app)

if __name__ == "__main__":
    main()
