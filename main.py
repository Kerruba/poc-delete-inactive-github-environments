import os
from github import Github
from github import Auth
from github import GithubException
from datetime import datetime
import requests


def delete_deployment(repo, id):
    resp = requests.delete(
        f"https://api.github.com/repos/{repo}/deployments/{id}",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    print(resp.text)
    return resp.status_code


def delete_environment(repo, environment_name):
    resp = requests.delete(
        f"https://api.github.com/repos/{repo}/environments/{environment_name}",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    print(resp.text)
    return resp.status_code


# GH_APP_TOKEN will require repository write permission and admistration permission
# To being able to delete deployments (and environment)
API_KEY = os.getenv("GH_APP_TOKEN")

if API_KEY is None:
    raise ValueError("Please define API_KEY as environment var!")

DELETE_ENVIRONMENTS = os.getenv("DELETE_ENVIRONMENTS") or None

repositories = [
    "camunda/operate",  # Operate
    "camunda/cawemo",  # Cawemo
    "camunda/camunda",  # Monorepo
    "camunda/camunad-optimize",  # Optimize
    "camunda/tasklist",  # Task-list
    "camunda/web-modeler",  # Web-modeler
]

# Authenticate with GitHub API
auth = Auth.Token(API_KEY)
g = Github(auth=auth)

for repo_name in repositories:

    repo = g.get_repo(repo_name)

    deployments = repo.get_deployments()
    count = {"active": 0, "deleted": 0, "deactivated": 0}

    for depo in deployments:
        branch = depo.ref
        name = depo.environment
        updated_at = depo.updated_at
        now = datetime.now()
        statuses = depo.get_statuses()
        print(
            f"Inspecting Deployment {name} of branch {branch} ({statuses[0].state})- Last Updated ({updated_at})"
        )

        if branch == "master" or "main" or "stable/" in branch:
            # Assumption: The first status in the array defines the current status of a deployment
            if statuses[0].state != "inactive":
                print("Ignoring active stable / master deployment")
                count["active"] += 1
                continue
            else:
                print("Deleting inactive stable / master deployment")
                delete_deployment(repo_name, depo.id)
                count["deleted"] += 1
        else:
            print(f"Checking whether branch {branch} still exists")
            try:
                repo.get_branch(branch=branch)
                print("Branch still exists - not deleting deployment")
                count["active"] += 1
                continue
            except GithubException:
                print(f"GitHub branch {branch} doesnt exist anymore")
                print(f"Deleting GH Deployment - {name}")

                status_code = delete_deployment(repo_name, depo.id)

                # 422 - We cannot delete an active deployment unless it is the only deployment in a given environment.
                if status_code == 422:
                    depo.create_status(state="inactive", auto_inactive=True)
                    delete_deployment(repo_name, depo.id)
                    count["deactivated"] += 1

                if DELETE_ENVIRONMENTS == "true":
                    environment_name = depo.environment
                    print(f"Deleting GH Environment - {environment_name}")
                    delete_environment(repo_name, environment_name)

                count["deleted"] += 1

        print(f"Finished processing deployments for repository {repo_name}")
        print("========================================")
        print("Summary:")
        print("Active Deployments: ", count["active"])
        print("Deleted Deployments: ", count["deleted"])
        print("Deactivated Deployments: ", count["deactivated"])
