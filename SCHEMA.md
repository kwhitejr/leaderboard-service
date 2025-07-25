# DynamoDB Schema Design

## Table: leaderboard-scores

### Primary Key Structure

- **Partition Key**: `game_id` (String)
- **Sort Key**: `sort_key` (String) - Format: `{score_type}#{formatted_score}`

### Sort Key Design

The sort key is designed to enable efficient leaderboard queries:

1. **High Score** (`high_score`): Uses negative score for descending order
   - Format: `high_score#-000000103.000`
   - Higher scores appear first when querying

2. **Fastest Time** (`fastest_time`): Uses positive score for ascending order
   - Format: `fastest_time#000000034.700`
   - Faster (lower) times appear first when querying

3. **Longest Time** (`longest_time`): Uses negative score for descending order
   - Format: `longest_time#-000000087.500`
   - Longer (higher) times appear first when querying

### Item Attributes

- `game_id`: String - Partition key
- `sort_key`: String - Sort key (composite)
- `initials`: String - Player initials (max 3 chars)
- `score`: Number - Original score value
- `score_type`: String - One of: high_score, fastest_time, longest_time
- `timestamp`: String - ISO format timestamp

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