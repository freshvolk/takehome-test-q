variable "kubectl_context" {
  type        = string
  description = "kubectl context to deploy into"
}

variable "kubeconfig_path" {
  type        = string
  description = "path to kubeconfig"
  default     = "~/.kube/config"
}

variable "app_version" {
  type        = string
  description = "version of the app to deploy"
}

variable "app_name" {
  type        = string
  default     = "quilter-takehome-app"
  description = "image name if different from app_name"
}
