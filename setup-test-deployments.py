import os
import logging
import requests
from github import Github, GithubException
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
repo = g.get_repo(repo_name)
logger.info(f"Preparing repository {repo_name} for testing")


logger.info("Cleaning up all existing deployments")
deployments = repo.get_deployments()
for d in deployments:
    d.create_status("inactive", description="Inactive")
    status_code = delete_deployment(repo_name, d.id)

# Create deployments/environments for existing branches
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
    logger.info("Created '%s' deployment (status=%s) for branch %s", env, state, ref)

# Create deployments/environments for deleted branches
logger.info("Simulating deployment for delete branch")
main_ref = repo.get_git_ref("heads/main")
try:

    # Create branch
    logger.info("Creating ref /refs/heads/feat2")
    ref = repo.create_git_ref(ref="refs/heads/feat2", sha=main_ref.object.sha)

    # Create deployment and set as inactive
    logger.info("Creating inactive deployment for ref /refs/heads/feat2")
    d = repo.create_deployment(
        ref=ref.ref,
        environment="feat2_preview_env",
        description="Preview environment for feat2 branch",
    )
    d.create_status("inactive")
    #
    # Delete branch
    logger.info("Deleting branch feat2")
    ref.delete()
except GithubException as e:
    logger.error(e)
