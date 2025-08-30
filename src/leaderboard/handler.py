"""Lambda handler for leaderboard service."""

from typing import Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from .models import ScoreSubmission, ScoreType
from .service import LeaderboardService

logger = Logger()
app = APIGatewayRestResolver()
service = LeaderboardService()


@app.get("/leaderboard/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return service.health_check()


@app.post("/leaderboard/scores/v1")
def submit_score() -> dict[str, str]:
    """Submit a score to the leaderboard."""
    try:
        # Parse and validate request body
        submission = ScoreSubmission.model_validate(app.current_event.json_body)
        logger.info(
            "Score submission received", extra={"submission": submission.model_dump()}
        )

        # Delegate to service layer
        result = service.submit_score(submission)
        logger.info(
            "Score submitted successfully", extra={"game_id": submission.game_id}
        )

        return result

    except ValidationError as e:
        logger.warning("Invalid score submission", extra={"errors": e.errors()})
        raise BadRequestError(f"Invalid request: {e}") from e
    except RuntimeError as e:
        logger.error("Database error", extra={"error": str(e)})
        raise
    except Exception as e:
        logger.error("Unexpected error", extra={"error": str(e)})
        raise


@app.get("/leaderboard/leaderboards/v1/<game_id>")
def get_leaderboard(game_id: str) -> dict[str, Any]:
    """Get leaderboard for a specific game."""
    try:
        # Get query parameters
        score_type_param = app.current_event.get_query_string_value(
            "score_type", "HIGH_SCORE"
        )
        limit_param = app.current_event.get_query_string_value("limit", "10")

        # Validate parameters
        try:
            score_type = ScoreType(score_type_param)
        except ValueError as ve:
            raise BadRequestError(
                f"Invalid score_type: {score_type_param}. Must be one of: {[t.value for t in ScoreType]}"
            ) from ve

        try:
            limit = int(limit_param) if limit_param else 10
            if limit < 1 or limit > 100:
                raise ValueError()
        except ValueError as ve:
            raise BadRequestError(
                "Invalid limit: must be an integer between 1 and 100"
            ) from ve

        logger.info(
            "Leaderboard request",
            extra={"game_id": game_id, "score_type": score_type.value, "limit": limit},
        )

        # Delegate to service layer
        response = service.get_leaderboard(game_id, score_type, limit)

        logger.info(
            "Leaderboard retrieved successfully",
            extra={"game_id": game_id, "entries_count": len(response.leaderboard)},
        )

        return response.model_dump(mode="json")

    except ValueError as e:
        logger.warning("Invalid leaderboard request", extra={"error": str(e)})
        raise BadRequestError(str(e)) from e
    except RuntimeError as e:
        logger.error("Database error", extra={"error": str(e)})
        raise
    except Exception as e:
        logger.error("Unexpected error", extra={"error": str(e)})
        raise


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda handler entry point."""
    return app.resolve(event, context)
