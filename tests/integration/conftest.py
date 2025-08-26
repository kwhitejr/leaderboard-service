"""Integration test configuration and fixtures."""

import json
import os
import time
from collections.abc import Generator

import boto3
import pytest
from testcontainers.localstack import LocalStackContainer

from src.leaderboard.database import LeaderboardDatabase


@pytest.fixture(scope="session")
def localstack_container() -> Generator[LocalStackContainer, None, None]:
    """Start LocalStack container for integration tests."""
    with LocalStackContainer(image="localstack/localstack:3.0") as localstack:
        localstack.with_services("dynamodb", "lambda", "apigateway")

        # Wait for LocalStack to be ready
        time.sleep(2)

        # Set AWS environment variables for tests
        os.environ["AWS_ENDPOINT_URL"] = localstack.get_url()
        os.environ["AWS_ACCESS_KEY_ID"] = "test"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test"  # noqa: S105
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

        yield localstack


@pytest.fixture(scope="session")
def dynamodb_client(localstack_container: LocalStackContainer):
    """Create DynamoDB client connected to LocalStack."""
    return boto3.client(
        "dynamodb",
        endpoint_url=localstack_container.get_url(),
        aws_access_key_id="test",
        aws_secret_access_key="test",  # noqa: S106
        region_name="us-east-1",
    )


@pytest.fixture(scope="session")
def dynamodb_table(dynamodb_client, localstack_container: LocalStackContainer):
    """Create and configure DynamoDB table for tests."""
    table_name = "leaderboard-scores-test"

    # Create table
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "game_id", "KeyType": "HASH"},
                {"AttributeName": "sort_key", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "game_id", "AttributeType": "S"},
                {"AttributeName": "sort_key", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Wait for table to be active
        waiter = dynamodb_client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)

    except dynamodb_client.exceptions.ResourceInUseException:
        # Table already exists
        pass

    # Set environment variable so our code uses the test table
    os.environ["LEADERBOARD_TABLE"] = table_name

    yield table_name

    # Cleanup
    try:
        dynamodb_client.delete_table(TableName=table_name)
    except Exception:
        # Cleanup failed, but continue - this is expected during teardown
        pass  # noqa: S110


@pytest.fixture
def leaderboard_db(dynamodb_table: str, localstack_container: LocalStackContainer):
    """Create LeaderboardDatabase instance connected to test table."""
    # Override the table name and endpoint for testing
    original_table_name = os.environ.get("LEADERBOARD_TABLE")

    os.environ["LEADERBOARD_TABLE"] = dynamodb_table

    # Create database instance
    db = LeaderboardDatabase(table_name=dynamodb_table)

    # Override the DynamoDB resource to use LocalStack endpoint
    db.dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=localstack_container.get_url(),
        aws_access_key_id="test",
        aws_secret_access_key="test",  # noqa: S106
        region_name="us-east-1",
    )
    db.table = db.dynamodb.Table(dynamodb_table)

    yield db

    # Cleanup - clear all items from table
    try:
        # Scan all items and delete them
        response = db.table.scan()
        with db.table.batch_writer() as batch:
            for item in response.get("Items", []):
                batch.delete_item(
                    Key={"game_id": item["game_id"], "sort_key": item["sort_key"]}
                )
    except Exception:
        # Cleanup failed, but continue - this is expected during teardown
        pass  # noqa: S110

    # Restore original table name
    if original_table_name:
        os.environ["LEADERBOARD_TABLE"] = original_table_name


@pytest.fixture
def api_gateway_event_template() -> dict:
    """Template for API Gateway event structure."""
    return {
        "resource": "",
        "path": "",
        "httpMethod": "",
        "headers": {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "integration-test",
        },
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": None,
        "stageVariables": None,
        "requestContext": {
            "resourceId": "test",
            "resourcePath": "",
            "httpMethod": "",
            "extendedRequestId": "test",
            "requestTime": "01/Jan/2024:00:00:00 +0000",
            "path": "",
            "accountId": "123456789012",
            "protocol": "HTTP/1.1",
            "stage": "test",
            "domainPrefix": "test",
            "requestTimeEpoch": 1704067200000,
            "requestId": "test-request-id",
            "identity": {
                "cognitoIdentityPoolId": None,
                "accountId": None,
                "cognitoIdentityId": None,
                "caller": None,
                "sourceIp": "127.0.0.1",
                "principalOrgId": None,
                "accessKey": None,
                "cognitoAuthenticationType": None,
                "cognitoAuthenticationProvider": None,
                "userArn": None,
                "userAgent": "integration-test",
                "user": None,
            },
            "domainName": "test.execute-api.us-east-1.amazonaws.com",
            "apiId": "test",
        },
        "body": None,
        "isBase64Encoded": False,
    }


@pytest.fixture
def sample_score_data() -> dict:
    """Sample score submission data for tests."""
    return {
        "game_id": "integration_test_game",
        "initials": "INT",
        "score": 1000.0,
        "score_type": "high_score",
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context for testing."""

    class MockLambdaContext:
        def __init__(self):
            self.function_name = "leaderboard-test"
            self.function_version = "$LATEST"
            self.invoked_function_arn = (
                "arn:aws:lambda:us-east-1:123456789012:function:leaderboard-test"
            )
            self.memory_limit_in_mb = 128
            self.remaining_time_in_millis = lambda: 30000
            self.log_group_name = "/aws/lambda/leaderboard-test"
            self.log_stream_name = "2024/01/01/[$LATEST]test"
            self.aws_request_id = "test-request-id"

    return MockLambdaContext()


def create_api_event(
    method: str,
    path: str,
    body: dict = None,
    query_params: dict = None,
    path_params: dict = None,
    template: dict = None,
) -> dict:
    """Helper function to create API Gateway events."""
    if template is None:
        # Create a basic template if none provided
        template = {
            "resource": path,
            "path": path,
            "httpMethod": method,
            "headers": {"Content-Type": "application/json"},
            "queryStringParameters": query_params,
            "pathParameters": path_params,
            "body": json.dumps(body) if body else None,
            "isBase64Encoded": False,
            "requestContext": {"httpMethod": method, "path": path, "stage": "test"},
        }
    else:
        # Use provided template and override specific fields
        template = template.copy()
        template["resource"] = path
        template["path"] = path
        template["httpMethod"] = method
        template["queryStringParameters"] = query_params
        template["pathParameters"] = path_params
        template["body"] = json.dumps(body) if body else None
        template["requestContext"]["httpMethod"] = method
        template["requestContext"]["path"] = path

    return template
