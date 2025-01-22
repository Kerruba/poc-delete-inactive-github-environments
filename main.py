import os
import logging
from github import Github
from github import Auth
from github import GithubException
from datetime import datetime
import requests

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def delete_deployment(repo, id):
    logger.info("Deleting deployemnt %s for repo %s", id, repo)
    resp = requests.delete(
        f"https://api.github.com/repos/{repo}/deployments/{id}",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    logger.debug("Response code: %d", resp.status_code)
    return resp.status_code


# GH_APP_TOKEN will require repository write permission and admistration permission
# To being able to delete deployments (and environment)
API_KEY = os.getenv("GH_APP_TOKEN")

if API_KEY is None:
    raise ValueError("Please define API_KEY as environment var!")

repositories = [
    "Kerruba/poc-delete-inactive-github-environments"
    # "camunda/operate",  # Operate
    # "camunda/cawemo",  # Cawemo
    # "camunda/camunda",  # Monorepo
    # "camunda/camunad-optimize",  # Optimize
    # "camunda/tasklist",  # Task-list
    # "camunda/web-modeler",  # Web-modeler
]

# Authenticate with GitHub API
auth = Auth.Token(API_KEY)
g = Github(auth=auth)

for repo_name in repositories:
    logger.info("Processing deployments for repository %s", repo_name)

    repo = g.get_repo(repo_name)

    deployments = repo.get_deployments()
    count = {"active": 0, "deleted": 0, "deactivated": 0}

    for depo in deployments:
        branch = depo.ref
        name = depo.environment
        last_state = depo.get_statuses()[0].state
        logger.debug(
            f"Inspecting Deployment {name} of branch {branch} ({last_state})- Last Updated ({depo.updated_at})"
        )

        if branch in ("master", "main") or branch.startswith("stable/"):
            # Assumption: The first status in the array defines the current status of a deployment
            if last_state != "inactive":
                logger.info("Ignoring %s main / master / stable deployment", last_state)
                count["active"] += 1
                continue
            else:
                logger.info("Deleting %s main / master / stable deployment", last_state)
                status_code = delete_deployment(repo_name, depo.id)
                logger.info("Deleted deployment with status code %d", status_code)
        else:
            logger.info("Checking whether branch %s still exists", branch)
            try:
                repo.get_branch(branch=branch)
                logger.info("Branch %s still exists - not deleting deployment", branch)
                count["active"] += 1
                continue
            except GithubException as e:
                if e.status == 404:
                    logger.warning(f"GitHub branch {branch} doesnt exist anymore")
                    logger.info(f"Deleting GH Deployment - {name}")

                    status_code = delete_deployment(repo_name, depo.id)

                    # 422 - We cannot delete an active deployment unless it is the only deployment in a given environment.
                    if status_code == 422:
                        logger.warning("Deployment is active - deactivating")
                        depo.create_status(state="inactive", auto_inactive=True)
                        delete_deployment(repo_name, depo.id)

                    count["deleted"] += 1
                else:
                    logger.warning("GET branch %s response code: %d", branch, e.status)

    logger.info("========================================")
    logger.info("Finished processing deployments for repository %s", repo_name)
    logger.info("========================================")
    logger.info("Summary:")
    logger.info("Active Deployments: %d", count["active"])
    logger.info("Deleted Deployments: %d", count["deleted"])
    logger.info("Deactivated Deployments: %d", count["deactivated"])
