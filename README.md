# Leaderboard Microservice

A serverless leaderboard service built with AWS Lambda, DynamoDB, and Python. Supports multiple score types including high scores, fastest times, and longest times.

## Features

- **Multiple Score Types**: High score, fastest time, longest time
- **Classic Arcade Format**: 3-letter initials with scores
- **RESTful API**: Clean versioned endpoints following `/{domain}/{resource}/{version}` pattern
- **Serverless**: Built for AWS Lambda with DynamoDB
- **Low Cost**: Optimized for demo games with pay-per-use pricing

## API Endpoints

### Submit Score
```
POST /games/scores/v1
Content-Type: application/json

{
  "game_id": "snake_classic",
  "initials": "KMW",
  "score": 103.0,
  "score_type": "high_score"
}
```

### Get Leaderboard
```
GET /games/leaderboards/v1/{game_id}?score_type=high_score&limit=10
```

Response:
```json
{
  "game_id": "snake_classic",
  "score_type": "high_score",
  "leaderboard": [
    {
      "rank": 1,
      "initials": "KMW",
      "score": 103.0,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

## Score Types

- `high_score`: Higher values rank better (e.g., points, kills)
- `fastest_time`: Lower values rank better (e.g., race times, speedruns)
- `longest_time`: Higher values rank better (e.g., survival time)

## Development Setup

### Prerequisites
- Python 3.11+
- AWS CLI configured
- Terraform (for infrastructure)

### Local Development
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run linting
black src/ tests/
ruff src/ tests/
mypy src/

# Run mutation tests
mutmut run
```

### Project Structure
```
├── src/leaderboard/          # Source code
│   ├── handler.py           # Lambda handler
│   ├── models.py            # Pydantic models
│   └── database.py          # DynamoDB operations
├── tests/                   # Unit tests
├── terraform/               # Infrastructure as code
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Development dependencies
└── SCHEMA.md               # Database schema documentation
```

## Database Schema

The service uses a single DynamoDB table with:
- **Partition Key**: `game_id`
- **Sort Key**: `sort_key` (format: `{score_type}#{formatted_score}`)

See [SCHEMA.md](SCHEMA.md) for detailed schema design.

## Deployment

### Infrastructure
```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

### Function Deployment
The GitHub Actions pipeline automatically deploys on pushes to main branch.

## Integration with Godot

The API is designed for easy integration with Godot's HTTPRequest node:

```gdscript
# Submit score
func submit_score(game_id: String, initials: String, score: float, score_type: String):
    var http_request = HTTPRequest.new()
    add_child(http_request)
    
    var data = {
        "game_id": game_id,
        "initials": initials,
        "score": score,
        "score_type": score_type
    }
    
    var json_data = JSON.stringify(data)
    var headers = ["Content-Type: application/json"]
    
    http_request.request("https://api.kwhitejr.com/games/scores/v1", headers, HTTPClient.METHOD_POST, json_data)

# Get leaderboard
func get_leaderboard(game_id: String, score_type: String = "high_score", limit: int = 10):
    var http_request = HTTPRequest.new()
    add_child(http_request)
    
    var url = "https://api.kwhitejr.com/games/leaderboards/v1/%s?score_type=%s&limit=%d" % [game_id, score_type, limit]
    http_request.request(url)
```