GET_APP_BASIC_INFO = """
query getApps($filter: AppFilter) {
  apps(filter: $filter) {
    nodes {
      title
      slug
      created_at
      author {
        username
      }
    }
    pageInfo {
      hasNextPage
    }
  }
}
"""

GET_APP_SERVICES = """
query getServices($slug: String!) {
  app(slug: $slug) {
    services {
      type
      name
      config
    }
  }
}
"""

GET_ENV_VARIABLES = """
query getEnvVars($slug: String!) {
  app(slug: $slug) {
    environment_variables {
      key
      value
      description
    }
  }
}
"""

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

UPDATE_APP_MUTATION = """
mutation updateApp($input: AppUpdate!) {
  updateOneApp(input: $input) {
    app_id
  }
}
"""

CREATE_SERVICE_MUTATION = """
mutation createService($input: ServiceInput!) {
  createOneService(input: $input) {
    service_id
    name
  }
}
"""