import os
import logging
import requests
from github import Github
from github import Auth

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def delete_deployment(repo, id):
    resp = requests.delete(
        f"https://api.github.com/repos/{repo}/deployments/{id}",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    resp.raise_for_status()
    return resp.status_code


API_KEY = os.getenv("GH_APP_TOKEN")

if API_KEY is None:
    raise ValueError("Please define API_KEY as environment var!")

auth = Auth.Token(API_KEY)
g = Github(auth=auth)
repo_name = "Kerruba/poc-delete-inactive-github-environments"

# Cleanup all deployments and start fresh
repo = g.get_repo(repo_name)
deployments = repo.get_deployments()
for d in deployments:
    d.create_status("inactive", description="Inactive")
    status_code = delete_deployment(repo_name, d.id)
    print(status_code)


test_dep_tuples = [
    ("main", "production", "stable", "success"),
    ("feat1", "feat1_preview_env", "Preview environments for feat1 branch", "inactive"),
    (
        "stable/1.0",
        "stable_preview_env",
        "Preview environment for stable branch",
        "success",
    ),
]

for t in test_dep_tuples:
    ref = t[0]
    env = t[1]
    description = t[2]
    state = t[3]
    d = repo.create_deployment(ref=ref, environment=env, description=description)
    d.create_status(state)
    print(d)
