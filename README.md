# SGTM
One-way sync of GitHub pull requests to Asana tasks so engineers can track all of their work in Asana. To see a more detailed explanation of the functionality of SGTM, see the [code_reviews](docs/code_reviews.md) docs.

## Setup
Follow these instructions for setting up SGTM to run in your environment and your infrastructure! Note that this is currently only set up for deployment on AWS, so if you are using a cloud provider, you may need to modify some code and deploy the app yourself.

### Fork repository and set up your local repository
You will need to set some overrides specific to your deployment -- mostly due to the fact that AWS S3 bucket names are globally unique, but you may want to tweak some default configuration settings. So, we recommend forking this repository into your Github organization.

### Installation
We recommend setting up a virtual environment to install and run your python environment. By doing so, you can eliminate
the risk that SGTM's python dependencies and settings will be mixed up with any such dependencies and settings that you
may be using in other projects. Once you install `pipenv` (see [Installing a Virtual Environment for Python](#installing-a-virtual-environment-for-python) below),
you should install all required python dependencies using `pipenv install`.

### Install Terraform
You'll need to [install Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli) to launch the infrastructure for SGTM.

### Install Terragrunt
You'll need to [install Terragrunt](https://terragrunt.gruntwork.io/docs/getting-started/install/) to configure Terraform for your own account.

### Create your credentials for Asana/AWS/Github
There are three external services you'll need to interact with, and therefore need credentials for.

#### Asana
Create a [Personal Access Token](https://developers.asana.com/docs/personal-access-token) in Asana. At Asana, we created a [Guest Account](https://asana.com/guide/help/organizations/guests) to run SGTM as, so no engineer's personal access token is used, and it's clear that there's a specific "SGTM" user who is making the task updates.

Copy this Personal Access Token for the next step.

#### AWS
You'll need to be able to authenticate with AWS via the command line, and there are a few ways to achieve that. See [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) for your options, but most likely you'll already have a preferred method of interacting with AWS via the command line.

#### Github
Again, you will probably want to create a new Github user in your org that is just for SGTM (since SGTM will be updating/merging PRs, it's clearer to attribute those actions to a user that is clearly name "SGTM" or something similar).

1. For the Github user you want to use, generate a [Personal Access Token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) with the following permissions:
   * repo (Full control of private repositories)
   * read:org (Read org and team membership, read org projects)
2. Generate a [secret token](https://developer.github.com/webhooks/securing/) for your Github webhook. Github suggests generating this via `ruby -rsecurerandom -e 'puts SecureRandom.hex(20)'`, but use whatever method you are comfortable with to generate a secure secret token. Save this somewhere, as you'll need it twice in the later steps.

Copy this Personal Access Token for the next step.

### Create a file in S3 that maps github usernames to Asana user IDs

1. Create a file in S3 that maps github usernames to Asana user IDs. This file should be in the following format:
```
{
  "github_username1": "asana_user_id1",
  "github_username2": "asana_user_id2",
  ...
}
```
1. Save the S3 bucket name and the file name in `./terraform/terraform.tfvars.json` under `"github_usernames_to_asana_gids_s3_path"`.
2. (Optional) If the S3 bucket is not in the same AWS account as your SGTM deployment, ensure that the bucket policy on the S3 bucket allows the SGTM account to read from the bucket. Learn more about cross-account access to S3 bucket objects here: https://repost.aws/knowledge-center/cross-account-access-s3

### Create Asana Projects
You'll need to create an Asana project for your Github sync tasks.

1. To create your "SGTM <repo> tasks" project, use the `setup_sgtm_tasks_project.py` script. The script will prompt you for the PAT you generated earlier, and guide you through setting up a brand new project or updating an existing project with the recommended Custom Fields.
     ```
      >>> To setup a new project
      python3 scripts/setup_sgtm_tasks_project.py  -p "<PAT>" create -n "<PROJECT NAME>" -t "<TEAM ID>"

      >>> To update an existing project with the suggested custom fields
      python3 scripts/setup_sgtm_tasks_project.py  -p "<PAT>" update -e "<EXISTING PROJECT ID>"
      ```
    1. If you have multiple repositories you want synced to Asana, you can create several of these projects. Make sure to take note of all of the project IDs for a later step.
    2. If you are on Asana Basic and do not have access to Custom Fields, the script will skip that step - SGTM will work even without the suggested fields
2. Make sure that the Asana user/guest that you created earlier is a member of this projects.

### Set your Terraform variables
NOTE: AWS S3 Bucket names are globally unique, so you will need to choose your own bucket names to be unique that no other AWS account has already created.
1. In `./terraform/variables.tf`, any variable that is listed without a default value needs to be set. The preferred method of setting these values is through [environment variables](https://www.terraform.io/docs/cli/config/environment-variables.html#tf_var_name). For example, to se terraform variable `github_usernames_to_asana_gids_s3_path`, you'll want to set an environment variable `TF_VAR_github_usernames_to_asana_gids_s3_path`.
2. Save these somewhere that you and others collaborating on this deployment could share (we save ours in an Asana task internally, of course) since these will need to be the same each time you apply new changes.

### Run setup script
You'll first need to set up the [Terraform remote state](https://www.terraform.io/docs/state/remote.html) to be the source of truth for the state of your deployed infrastructure.

SGTM supports both s3 and terraform cloud backend. Please select only 1 to deploy your terraform changes to.

#### S3 Backend Setup

1. Run `python3 ./scripts/setup.py state` (this will create  an S3 bucket and DyanmoDb lock table for Terraform)
2. Ensure `TF_VAR_terraform_backend_use_tfc=false` and continue the setup instructions from Step #2 below.

#### Terraform Cloud Setup
You'll need to have a Terraform Cloud account have the workspace you want to deploy SGTM in already setup. Make sure you have admin/write access to the workspace

1. Set `TF_VAR_terraform_backend_use_tfc=true` and make sure the dependent TF_VARs are defined as well. (`TF_VAR_terraform_backend_organization_name` and `TF_VAR_terraform_backend_workspace_name`)
2. Initialize and apply the infrastructure:
```bash
> cd ./terraform
> terragrunt init
> terragrunt apply
```
3. Save the output of `terragrunt apply`, which should print out a `api_gateway_deployment_invoke_url`. You'll need this in the next step.
4. Push your secrets to the ecrypted S3 bucket that Terraform just created. `cd` back to the root of your repository and run: `python3 ./scripts/setup.py secrets` and follow the prompts.

### Add Mapping of Github Repository -> Asana Project
For each repository that you are going to sync:
1. Find that repository's Github Graphql `node_id`:
   1. You can get this using `curl -i -u <username>:<github_personal_access_token> https://api.github.com/repos/<organization>/<repository>`
2. Using the "SGTM tasks" project id from [Create Asana Projects](#create-asana-projects), update the sgtm-objects DynamoDb table with the mapping of `{"github-node": "<node_id>", "asana-id": "<project_id>"}`

### Create Your Github Webhook
For each repository that you want to sync to Asana through SGTM:
1. Navigate to `https://github.com/<organization>/<repository>/settings/hooks`
2. Click "Add webhook"
3. Under "Payload URL", input the `api_gateway_deployment_invoke_url` from the previous step
4. Under "Content Type", select "application/json"
5. Under "Secret", input your secret token that you generated earlier
6. Under "Which events would you like to trigger this webhook?", select "Let me select individual events."
   1. Issue comments
   2. Pull requests
   3. Pull request reviews
   4. Pull request review comments
   5. Statuses
7. Make sure "Active" is selected
8. Click "Add webhook"

### Take it for a spin!
At this point, you should be all set to start getting Pull Requests synced to Asana Tasks. Open up a Pull Request, and Enjoy!

## Optional Features
SGTM has a few optional power features that are disabled by default, but can be enabled with environment variables.
### Auto-merge pull requests
SGTM can merge your pull requests automatically when certain conditions are fulfilled. This behavior is controlled by adding labels to the PR in Github. If this feature is enabled, there are 3 different labels you can apply to your PR to cause the PR to be auto-merged under different conditions:
* 🔍 `merge after tests and approval`: auto-merge this PR once tests pass and the PR is approved
* 🧪 `merge after tests`: auto-merge this PR once tests pass (regardless of approval status)
* 🚢 `merge immediately`: auto-merge this PR immediately

In all cases, a PR with merge conflicts will not be auto-merged.

**How to enable**:
* Set an env variable of `TF_VAR_sgtm_feature__automerge_enabled` to `true`
* Create labels in your repository of `merge after tests and approval`, `merge after tests` and `merge immediately`

### Auto-complete linked tasks
At Asana, pull requests often have corresponding Asana tasks that can be completed when the pull request merges. With this feature enabled, setting a Github label of `complete tasks on merge` on a PR will automatically complete any linked Asana tasks. Asana tasks can be linked by adding their URLs to a line under the string `Asana tasks:` in the PR description, as demonstrated below:
```
Asana tasks:
<task_to_complete_url> <another_task_to_complete_url>
```
**How to enable**:
* Set an env variable of `TF_VAR_sgtm_feature__autocomplete_enabled` to `true`
* Create a label of `complete tasks on merge` in your repository

*Note*: If the SGTM user in your Asana domain doesn't have access to a linked task, it won't be able to merge it. You can add the SGTM user as a collaborator on a task to give it the ability to auto-complete the task.

### Select users for follow-up review
SGTM can avoid closing tasks if the approvals come from certain Github users.  This can be useful if you have specific Github users that you would like to be able to approve PRs in order to unblock merging, but that you want a second set of eyes on.
For example, you may have a bot that automatically approves certain auto-generated PRs to speed up some workflow, but you still want a human to review those changes afterwards.

**How to configure**:
* Set an env variable of `TF_VAR_sgtm_feature__followup_review_github_users` to contain a comma-separated list of Github usernames that should have follow-up review

### Turn off Github team task subscriptions to reduce inbox noise
By default SGTM subscribes every member of a reviewing Github team to the SGTM task. You might want to turn this off if you want to use team reviewers as a marker for PR ownership or triage, but don't need every member of that team to see each PR.

**How to configure**:
* Set an env variable of `TF_VAR_sgtm_feature__disable_github_team_subscription` to `true`

### Always set the Asana task assignee to be the author of the Github Pull Request
By default SGTM will assign the task corresponding to the PR to the assignee on the Github pull request. The assignee on the Asana task will change for the following events: when the PR is in draft status, when changes are requested on the PR, when the PR is approved, or when a review is requested. Turning this feature on will keep the assignee of the task corresponding to the PR to always be the author of the pull request. This is useful if you want to reduce Asana inbox noise from reassignment or if you prefer to have the author of the PR be responsible for the corresponding Asana task.

**How to configure**:
* Set an env variable of `TF_VAR_sgtm_feature__allow_persistent_task_assignee` to `true`
* Ensure that the PR has the `persistent task assignee` Github label attached to the PR.

### Rerun required checks on pull requests that are older than N hours with a specific base ref
SGTM can use Github API to rerun Check Runs on pull requests with a specified base ref if the results of those check runs exceeds a set number of hours. This is useful for keeping the status of your check runs "fresh" especially if the base ref is updated frequently. It will ignore pull requests that do not match the specified base ref.

*Note*: This does not use Github's check conclusion state `stale`.

**How to configure**:
* Set an env variable of `TF_VAR_sgtm_feature__check_rerun_base_ref_names` to contain a comma-separated list of ref names (e.g. `master`, `main`) that pull requests must be based off of to have their check runs rerequested. The default is `"main,master"`.
* Set an env variable of `TF_VAR_sgtm_feature__check_rerun_threshold_hours` to any positive integer to represent the number of hours before a check run will be rerequested. The default is `0` which disables the feature.

## Installing a Virtual Environment for Python

We recommend using `pipenv` to manage your python environment for SGTM. We've checked in a `Pipfile` and `Pipfile.lock` to make this easier for you. If you have `pipenv` installed, `cd` into the SGTM directory, and run `pipenv install` to install all dependencies. If you don't have `pipenv` installed, you can install it via `pip install pipenv`.

You can then run `pipenv shell` to enter the virtual environment from a specific shell session. Run `exit` to leave it.
Alternatively, you don't have to 'enter' the virtual environment - you can instead run a command inside the virtual environment by prefixing the command with `pipenv run`.

## Testing on Staging
SGTM's terraform configuration will also spin up a staging cluster that you can use for manual testing. To only deploy changes to staging, run `terragrunt apply --target=module.sgtm-staging`. To direct webhook events to your staging cluster, use API gateway endpoint `/sgtm_staging` instead of `/sgtm`.

You can also choose to create new staging clusters, by copying the `module "sgtm-staging"` in `main.tf`. Be sure to choose a new name for your staging cluster and update the `naming_suffix` parameter so that terraform doesn't override existing resources.

## Testing Locally
You can also choose to test your changes locally. Here are step-by-step instructions on how to test manually/locally:

1. Create a [Personal Access Token](https://developers.asana.com/docs/personal-access-token) in Asana. Copy that token and export it in your shell environment (`export ASANA_API_KEY=<your_asana_personal_access_token>`)
2. Create a Github Personal Access Token as per the instrucitons in the [Github](#github) section above. Export that token in your shell environment (`export GITHUB_API_KEY=<your_github_personal_access_token>`)
3. Follow the instructions in [Installing a Virtual Environment for Python](#installing-a-virtual-environment-for-python) to install necessary requirements.
4. Open up a `python` REPL in the `SGTM` root directory (or use `ipython`, but you'll have to `pipenv install ipython` first)
5. Run the function you want to test. It's usually fine / recommended to skip the DynamoDb locking when testing locally, since you usually won't be needing to test that. Here's an example of how to test updating a pull request:
    1. Note what code you want to test. In this case, we want to go to [src/github/webhook.py](/src/github/webhook.py) and look at `_handle_pull_request_webhook`. It looks like we need an `pull_request_id`.
    2. Get the `pull_request_id`. One easy way to do this is to run a command like this `curl -i -u <github_username>:$GITHUB_API_KEY https://api.github.com/repos/asana/sgtm/pulls/123` and then grab the `node_id` from that response.
    3. Open up your REPL. Import the function you want to test (in this case: `import src.github.controller as github_controller; import src.github.graphql.client as graphql_client`)
    4. Run the code! In this case:
        1. `pull_request = graphql_client.get_pull_request(<pull_request_id>)`
        2. `github_controller.upsert_pull_request(pull_request)`

## Running Tests

You may then run all tests via the command line:

```bash
TEST=1 python3 -m unittest discover
```

Alternatively, you may run specific tests e.g. via:

```bash
TEST=1 python3 -m unittest test/<python-test-file-name>.py
TEST=1 python3 -m unittest test.<python-test-module-name>.<TestClassName>
TEST=1 python3 -m unittest test.<python-test-module-name>.<TestClassName>.<test_function_name>
```

## "Building"
Please perform the following checks prior to pushing code

* run `black .` to autoformat your code
* run `mypy` on each file that you have changed
* run tests, as described in the [previous section](#running-tests)
