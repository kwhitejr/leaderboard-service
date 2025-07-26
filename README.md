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

# Run tests with coverage
pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

# Check coverage against dynamic threshold
python scripts/check-coverage.py

# Alternative: Use Makefile commands
make test                 # Run tests
make coverage            # Run tests with coverage report
make check-coverage      # Check against dynamic threshold
make lint                # Run all linting checks

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
├── scripts/                 # Development scripts
│   ├── check-coverage.py    # Dynamic coverage threshold checker
│   └── test-coverage-system.py # Coverage system test suite
├── .github/                 # GitHub Actions workflows
│   ├── coverage-baseline.json   # Dynamic coverage baseline
│   └── workflows/ci.yml     # CI/CD pipeline
├── terraform/               # Infrastructure as code
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Development dependencies
├── Makefile                 # Developer commands
├── .codecov.yml            # Codecov configuration
└── SCHEMA.md               # Database schema documentation
```

## Database Schema

The service uses a single DynamoDB table with:
- **Partition Key**: `game_id`
- **Sort Key**: `sort_key` (format: `{score_type}#{formatted_score}`)

See [SCHEMA.md](SCHEMA.md) for detailed schema design.

## Quality Assurance

### Test Coverage Protection

The project implements a **dynamic ratcheting coverage system** that prevents coverage regression while encouraging improvement:

- **Current Coverage**: 96.88% (32 tests)
- **Protection**: Coverage can never decrease below the established baseline
- **Growth**: When coverage improves, the baseline automatically updates
- **Enforcement**: Both local development and CI/CD pipeline enforcement

#### How It Works

1. **Baseline Tracking**: `.github/coverage-baseline.json` stores the current coverage floor
2. **Dynamic Checking**: `scripts/check-coverage.py` compares current coverage against baseline
3. **Automatic Updates**: Baseline increases automatically when coverage improves on main branch
4. **CI Integration**: GitHub Actions enforces coverage protection on all PRs

#### Developer Workflow

```bash
# Check coverage locally (same as CI)
make check-coverage

# Run coverage with detailed report
make coverage

# Test the coverage system
python scripts/test-coverage-system.py
```

The system ensures coverage can only stay the same or improve, creating a ratcheting effect that maintains high code quality standards.

### Mutation Testing

Beyond line coverage, the project uses **mutation testing** with `mutmut` to validate test quality by introducing deliberate code changes (mutations) and verifying that tests catch them.

#### What is Mutation Testing?

Mutation testing helps identify weaknesses in your test suite by:
- Creating small modifications to your source code (mutants)
- Running your tests against each mutant
- Reporting which mutants "survived" (weren't caught by tests)

#### Running Mutation Tests

```bash
# Run basic mutation tests
make mutate

# Run with HTML report for detailed analysis
make mutate-html

# Interactive browser for mutation results
make mutate-browse

# View results summary
make mutate-results

# Clean up mutation artifacts
make mutate-clean
```

#### Interpreting Results

- **Killed mutants**: Good! Your tests caught the change
- **Surviving mutants**: Areas where tests might be improved
- **Timeout/Error mutants**: Usually indicate infrastructure issues

A typical mutation score of 70-80% is considered good, with 90%+ being excellent.

#### Mutation Testing Workflow

1. **Run initial mutation test**: `make mutate`
2. **Analyze survivors**: `make mutate-browse`
3. **Improve tests**: Add tests to catch surviving mutants
4. **Re-test**: Run mutation tests again
5. **Iterate**: Continue until satisfied with mutation score

Mutation testing complements line coverage by ensuring tests actually validate logic, not just execute code paths.

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