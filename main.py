from gql import gql
from client import get_client
from datetime import datetime, timedelta
from pprint import pprint

# ------------------ GraphQL Queries ------------------

GET_APP_BASIC_INFO = """
query getAppBasicInfo($filter: AppFilter) {
  apps(
    filter: $filter
    sorting: [{ field: created_at, direction: ASC }]
    paging: { limit: 50 }
  ) {
    nodes {
      title
      slug
      author {
        username
      }
      created_at
    }
    pageInfo {
      hasNextPage
    }
  }
}
"""

GET_APP_SERVICES = """
query getAppServices($slug: String!) {
  app(slug: $slug) {
    services {
      name
      status
      type
    }
  }
}
"""

GET_ENV_VARIABLES = """
query getEnvVars($slug: String!) {
  app(slug: $slug) {
    environment_variables(
      filter: {}
      sorting: [{ field: created_at, direction: ASC }]
    ) {
      key
      value
      type
      description
    }
  }
}
"""

# ------------------ App Info Fetcher ------------------

def get_app_basic_info():
    client = get_client()
    all_apps = []
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

            result = client.execute(
                gql(GET_APP_BASIC_INFO),
                variable_values={"filter": filter_arg},
            )

            apps = result["apps"]["nodes"]
            all_apps.extend(apps)

            page_info = result["apps"]["pageInfo"]
            if not page_info["hasNextPage"] or not apps:
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

        return all_apps

    except Exception as e:
        print(f"Error fetching app basic info: {str(e)}")
        return []

# ------------------ Main Execution ------------------

def fetch_all_app_data():
    client = get_client()
    apps_info = get_app_basic_info()
    compiled_apps_data = []

    for app in apps_info:
        slug = app["slug"]
        app_data = {
            "title": app.get("title") or "Untitled",
            "slug": slug,
            "author": app["author"]["username"],
            "created_at": app["created_at"],
            "services": [],
            "env_vars": [],
        }

        # Fetch services
        try:
            service_result = client.execute(
                gql(GET_APP_SERVICES), variable_values={"slug": slug}
            )
            app_data["services"] = service_result["app"]["services"]
        except Exception as e:
            print(f"Error fetching services for {slug}: {e}")

        # Fetch env vars
        try:
            env_result = client.execute(
                gql(GET_ENV_VARIABLES), variable_values={"slug": slug}
            )
            app_data["env_vars"] = env_result["app"]["environment_variables"]
        except Exception as e:
            print(f"Error fetching env vars for {slug}: {e}")

        compiled_apps_data.append(app_data)

    return compiled_apps_data


CREATE_APP_MUTATION = """
mutation createApp($input: CreateOneAppInput!) {
  createOneApp(input: $input) {
    app_id
    title
    slug
    created_at
  }
}
"""

def create_app_on_server(app_data):
    client = get_client()

    input_payload = {
        "input": {
            "app": {
                "title": app_data["title"],
                "slug": f"{app_data['slug']}-copy",
                "description": f"Cloned app originally created by {app_data['author']} on {app_data['created_at']}",
                "visible_on_portal": True,
                "maintainer_name": app_data["author"],
                "maintainer_email": f"{app_data['author']}@example.com",
                "view_access": "PUBLIC",
                "edit_access": "PRIVATE",
                "app_type": "classic",  # Or "appstudio" if that's relevant
                "python_version": "3.10",  # Or whatever default
            }
        }
    }

    try:
        result = client.execute(
            gql(CREATE_APP_MUTATION),
            variable_values=input_payload
        )
        created_app = result["createOneApp"]
        print(f"✅ Created app: {created_app['slug']} (ID: {created_app['app_id']})")
        return created_app
    except Exception as e:
        print(f"❌ Error creating app {app_data['slug']}: {e}")
        return None



# ------------------ Run ------------------

if __name__ == "__main__":
    fetched_apps = fetch_all_app_data()

    for app in fetched_apps:
        
        if app['title'] == "dashauth-test":
          create_app_on_server(app)
