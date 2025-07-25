variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "service_name" {
  description = "Name of the service"
  type        = string
  default     = "leaderboard"
}

variable "api_domain_name" {
  description = "Domain name for the API"
  type        = string
  default     = "api.kwhitejr.com"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "leaderboard-service"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}