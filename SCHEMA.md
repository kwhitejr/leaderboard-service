# DynamoDB Schema Design

## Table: leaderboard-scores

### Primary Key Structure

- **Partition Key**: `game_id` (String)
- **Sort Key**: `sort_key` (String) - Format: `{score_type}#{formatted_score}`

### Sort Key Design

The sort key is designed to enable efficient leaderboard queries:

1. **Points** (`POINTS`): Used for high score leaderboards
   - Format: `POINTS#000000103.000`
   - Application logic handles sorting for different leaderboard types

2. **Time in Milliseconds** (`TIME_IN_MILLISECONDS`): Used for time-based leaderboards
   - Format: `TIME_IN_MILLISECONDS#000000034.700`
   - Application logic handles sorting for fastest/longest time leaderboards

### Item Attributes

- `game_id`: String - Partition key
- `sort_key`: String - Sort key (composite format: `{score_type}#{formatted_score}`)
- `label`: String - Player identifier (username, initials, team name, etc.)
- `label_type`: String - Type of label: INITIALS, USERNAME, TEAM_NAME, CUSTOM
- `score`: Number - Original score value
- `score_type`: String - One of: POINTS, TIME_IN_MILLISECONDS
- `timestamp`: String - ISO format timestamp (stored as DynamoDB field, mapped to `created_at_timestamp` in API responses)

### Query Patterns

1. **Get leaderboard for specific game and score type**:
   ```
   KeyConditionExpression: game_id = :game_id AND begins_with(sort_key, :score_type_prefix)
   ```

2. **Get all score types for a game**:
   ```
   KeyConditionExpression: game_id = :game_id
   ProjectionExpression: score_type
   ```

### Benefits

- Single table design minimizes costs
- Efficient sorting without secondary indexes
- Supports multiple score types per game
- Natural leaderboard ordering through key design