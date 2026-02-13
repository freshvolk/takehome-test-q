terraform {
  required_version = "~> 1.5.7"

  required_providers {
    kubernetes = "~> 3.0.1"
  }
}

provider "kubernetes" {
  config_path    = local.kubeconfig_path
  config_context = local.kube_ctx
}

locals {
  kube_ctx        = var.kubectl_context
  app_name        = var.app_name
  prefix          = "${local.app_name}-${local.workspace}"
  kubeconfig_path = var.kubeconfig_path
  workspace       = terraform.workspace
}

resource "terraform_data" "workspace_check" {
  lifecycle {
    precondition {
      condition     = terraform.workspace != "default"
      error_message = "please use a workspace other than default. suggestions: dev, local-staging, etc"
    }
  }
}
