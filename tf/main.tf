locals {
  replicas = 1

  common_labels = {
    app         = local.app_name
    environment = local.workspace
  }
}

resource "kubernetes_namespace_v1" "env" {
  metadata {
    name   = local.workspace
    labels = local.common_labels
  }
}

resource "kubernetes_deployment_v1" "app" {
  metadata {
    name      = local.app_name
    namespace = kubernetes_namespace_v1.env.metadata[0].name
    labels    = local.common_labels
  }

  spec {
    replicas = local.replicas

    selector {
      match_labels = {
        app = local.app_name
      }
    }

    template {
      metadata {
        labels = local.common_labels
      }

      spec {
        container {
          name              = var.app_name
          image             = "${var.app_name}:${var.app_version}"
          image_pull_policy = "IfNotPresent"

          resources {
            requests = {
              cpu    = "100m"
              memory = "128Mi"
            }
            limits = {
              memory = "128Mi"
            }
          }

          port {
            container_port = 8000
          }

          liveness_probe {
            http_get {
              path = "/healthz"
              port = 8000
            }
          }

          readiness_probe {
            http_get {
              path = "/healthz"
              port = 8000
            }
          }
        }
      }
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "kubernetes_service_v1" "app" {
  metadata {
    name      = local.app_name
    namespace = kubernetes_namespace_v1.env.metadata[0].name
    labels    = local.common_labels
  }

  spec {
    selector = {
      app = local.app_name
    }

    port {
      port        = 8000
      target_port = 8000
    }
  }

  depends_on = [kubernetes_namespace_v1.env]
}
