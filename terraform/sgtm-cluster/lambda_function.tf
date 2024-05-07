
resource "aws_lambda_function" "sgtm" {
  s3_bucket        = var.lambda_code_s3_bucket_name
  s3_key           = aws_s3_object.lambda_code_bundle.key
  function_name    = "sgtm${local.cluster_suffix}"
  role             = aws_iam_role.sgtm_lambda.arn
  handler          = "src.handler.handler"
  source_code_hash = data.archive_file.create_dist_pkg.output_base64sha256

  runtime = var.lambda_runtime

  timeout = var.lambda_function_timeout
  environment {
    variables = {

      # general config
      API_KEYS_S3_BUCKET = var.api_key_s3_bucket_name,
      API_KEYS_S3_KEY    = var.api_key_s3_object,
      SQS_URL            = aws_sqs_queue.sgtm-webhooks-queue-fifo.url

      # SGTM features
      SGTM_FEATURE__AUTOMERGE_ENABLED                = var.sgtm_feature__automerge_enabled,
      SGTM_FEATURE__AUTOCOMPLETE_ENABLED             = var.sgtm_feature__autocomplete_enabled,
      SGTM_FEATURE__DISABLE_GITHUB_TEAM_SUBSCRIPTION = var.sgtm_feature__disable_github_team_subscription,
      SGTM_FEATURE__ALLOW_PERSISTENT_TASK_ASSIGNEE   = var.sgtm_feature__allow_persistent_task_assignee,
      SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS     = var.sgtm_feature__followup_review_github_users,
      SGTM_FEATURE__CHECK_RERUN_THRESHOLD_HOURS      = var.sgtm_feature__check_rerun_threshold_hours,
      SGTM_FEATURE__CHECK_RERUN_BASE_REF_NAMES       = var.sgtm_feature__check_rerun_base_ref_names,
      SGTM_FEATURE__CHECK_RERUN_ON_APPROVAL_ENABLED  = var.sgtm_feature__check_rerun_on_approval_enabled

      # github usernames to asana IDs mapping
      GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH = var.github_usernames_to_asana_gids_s3_path

      # variables used for Github Authentication
      GITHUB_APP_NAME                                    = var.github_app_name
      GITHUB_APP_INSTALLATION_ACCESS_TOKEN_RETRIEVAL_URL = var.github_app_installation_access_token_retrieval_url
    }
  }
}

locals {
  dist_dir_name = "lambda_dist_pkg/pkg${local.cluster_suffix}"
}

resource "null_resource" "install_python_dependencies" {
  triggers = {
    src_sha1 = sha1(join("", [for f in fileset(path.root, "../src/**") : filesha1(f)]))
  }

  provisioner "local-exec" {
    command = "bash ${path.module}/../../scripts/create_pkg.sh"

    environment = {
      source_code_path = "../src"
      PIPENV_PIPFILE   = replace(path.cwd, "/terraform", "/Pipfile")
      function_name    = "sgtm"
      runtime          = var.lambda_runtime
      path_cwd         = path.cwd
      dist_dir_name    = local.dist_dir_name
    }
  }
}

data "archive_file" "create_dist_pkg" {
  depends_on  = [null_resource.install_python_dependencies]
  source_dir  = "${path.cwd}/${local.dist_dir_name}"
  output_path = "build/pkg${local.cluster_suffix}/function.zip"
  type        = "zip"
}

resource "aws_s3_object" "lambda_code_bundle" {
  ## The lambda code bundle is created by the null_resource.install_python_dependencies
  depends_on  = [null_resource.install_python_dependencies]
  bucket      = var.lambda_code_s3_bucket_name
  key         = "sgtm_bundle${local.cluster_suffix}.zip"
  source      = data.archive_file.create_dist_pkg.output_path
  source_hash = data.archive_file.create_dist_pkg.output_base64sha256
}
