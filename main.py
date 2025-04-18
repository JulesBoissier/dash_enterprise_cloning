import os
from gql import gql
from datetime import datetime, timedelta
from client import get_client
from queries import (
    GET_APP_BASIC_INFO,
    GET_APP_SERVICES,
    GET_ENV_VARIABLES,
    CREATE_APP_MUTATION,
    UPDATE_APP_MUTATION,
    CREATE_SERVICE_MUTATION
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



# 2. Fetch the basic info of all apps
def fetch_all_apps():
    client = get_client()
    all_apps = []
    filter_arg = {}
    last_created_at = None

    try:
        while True:
            filter_arg = (
                {
                    "created_at": {
                        "gt": last_created_at,
                    },
                }
                if last_created_at
                else {}
            )

            filter_arg = {"filter": filter_arg}

            result = client.execute(gql(GET_APP_BASIC_INFO), variable_values=filter_arg)

            apps = result["apps"]["nodes"]
            all_apps.extend(apps)

            page_info = result["apps"]["pageInfo"]
            if not page_info["hasNextPage"]:
                break

            last_created_at = apps[-1]["created_at"]

            last_created_datetime = datetime.fromisoformat(
                last_created_at.replace("Z", "+00:00")
            )
            new_last_created_datetime = last_created_datetime + timedelta(
                milliseconds=1
            )
            last_created_at = new_last_created_datetime.isoformat().replace(
                "+00:00", "Z"
            )

        return [
            {
                "app_name": (app["title"] if app["title"] else app["slug"]),
                "author": app["author"]["username"],
                "slug": app["slug"],
                "created_at": datetime.fromisoformat(app["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d"),
            }
            for app in all_apps
        ]
    except Exception as e:
        print(f"Error fetching app basic info: {str(e)}")
        return []

# 3. Fetch services for a given app
def fetch_services_for_app(slug):
    variables = {"slug": slug}
    client = get_client()

    try:
        result = client.execute(gql(GET_APP_SERVICES), variable_values=variables)
        return result["app"]["services"]
    except Exception as e:
        print(f"Error fetching services for app {slug}: {str(e)}")
        return []

# 4. Fetch environment variables for a given app
def fetch_env_vars_for_app(slug):
    variables = {"slug": slug}
    client = get_client()

    try:
        result = client.execute(gql(GET_ENV_VARIABLES), variable_values=variables)
        return result["app"]["environment_variables"]
    except Exception as e:
        print(f"Error fetching env vars for app {slug}: {str(e)}")
        return []

# 5. Filter out protected environment variables
def filter_protected_env_vars(env_vars):
    return [
        {
            "key": var["key"],
            "value": var["value"],
            "description": var.get("description", ""),
        }
        for var in env_vars
        if var["key"] not in PROTECTED_ENV_KEYS
    ]

# 6. Create a new app (mutation)
def create_new_app(input_data):
    client = get_client()

    mutation = gql(CREATE_APP_MUTATION)

    variables = {
        "input": {
            "app": input_data
        }
    }

    try:
        result = client.execute(mutation, variable_values=variables)
        app_data = result["createOneApp"]
        print(f"✅ App created: {app_data['title']} (ID: {app_data['app_id']})")
        return app_data
    except Exception as e:
        print(f"❌ Error creating app: {e}")
        return None

# 7. Update environment variables for an existing app (mutation)
def update_app_env_vars(app_id, filtered_env_vars):
    client = get_client()

    mutation = gql(UPDATE_APP_MUTATION)

    variables = {
        "input": {
            "id": app_id,
            "app": {
                "environment_variables": filtered_env_vars
            }
        }
    }

    try:
        result = client.execute(mutation, variable_values=variables)
        print(f"✅ Updated env vars for app {app_id}")
    except Exception as e:
        print(f"❌ Error updating env vars for app {app_id}: {e}")

# 8. Add services to a newly created app
def add_services_to_app(app_id, services):
    client = get_client()

    for service in services:
        service_input = {
            "type": service["type"],
            "name": service["name"],
            "config": service["config"],
            "app_id": app_id
        }

        mutation = gql(CREATE_SERVICE_MUTATION)

        variables = {"input": service_input}

        try:
            result = client.execute(mutation, variable_values=variables)
            print(f"✅ Service {service['name']} added to app {app_id}")
        except Exception as e:
            print(f"❌ Error adding service {service['name']} to app {app_id}: {e}")

# 9. Clone an app including its services and environment variables
def clone_app(app_data):
    # Fetch original app's details
    slug = app_data["slug"]
    original_services = fetch_services_for_app(slug)
    original_env_vars = fetch_env_vars_for_app(slug)

    # Filter out protected environment variables
    filtered_env_vars = filter_protected_env_vars(original_env_vars)

    # Prepare input for the new app (this should come from your app_data)
    input_data = {
        "title": app_data["app_name"],
        "slug": f"{app_data['slug']}-copy",
        "description": f"Cloned app from {app_data['author']} on {datetime.now().isoformat()}",
        "visible_on_portal": True,
        "maintainer_name": app_data["author"],
        "maintainer_email": f"{app_data['author']}@example.com",
        "view_access": "PUBLIC",
        "edit_access": "PRIVATE",
        "app_type": "classic",
        "python_version": "3.10",
    }

    # 1. Create the new app
    new_app = create_new_app(input_data)
    if not new_app:
        return

    # 2. Update the environment variables for the new app
    update_app_env_vars(new_app["app_id"], filtered_env_vars)

    # 3. Add services to the new app
    add_services_to_app(new_app["app_id"], original_services)

# Main function to drive the cloning process
def main():
    apps = fetch_all_apps()

    for app in apps:
        if app['slug'] == 'dashauth-test':
            clone_app(app)

if __name__ == "__main__":
    main()
