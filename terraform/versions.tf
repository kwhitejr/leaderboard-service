terraform {
  required_version = ">= 1.0"

  backend "s3" {
    bucket = "leaderboard-terraform-state-prod"
    key    = "terraform.tfstate"
    region = "us-east-1"
    
    dynamodb_table = "leaderboard-terraform-locks"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}