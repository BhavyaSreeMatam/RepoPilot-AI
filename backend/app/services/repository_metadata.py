from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from fastapi import HTTPException

from app.core.config import get_settings


@lru_cache
def get_repository_table():
    """
    Return the RepoPilot DynamoDB repository metadata table.

    In production on EC2, boto3 automatically uses the EC2 IAM role.
    No AWS access keys are stored in the application.
    """

    settings = get_settings()

    dynamodb = boto3.resource(
        "dynamodb",
        region_name=settings.aws_region,
    )

    return dynamodb.Table(settings.repository_table_name)


def create_repository_metadata(
    owner_sub: str,
    repo_id: str,
    repo_name: str,
    original_filename: str,
) -> Dict[str, Any]:
    """
    Register a newly uploaded repository as belonging to one Cognito user.
    """

    item = {
        "owner_sub": owner_sub,
        "repo_id": repo_id,
        "repo_name": repo_name,
        "original_filename": original_filename,
        "indexed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    get_repository_table().put_item(
        Item=item,
        ConditionExpression=(
            "attribute_not_exists(owner_sub) "
            "AND attribute_not_exists(repo_id)"
        ),
    )

    return item


def get_repository_metadata(
    owner_sub: str,
    repo_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Return one repository only when it belongs to the supplied user.
    """

    response = get_repository_table().get_item(
        Key={
            "owner_sub": owner_sub,
            "repo_id": repo_id,
        }
    )

    return response.get("Item")


def require_repository_owner(
    owner_sub: str,
    repo_id: str,
) -> Dict[str, Any]:
    """
    Enforce repository ownership.

    Returns 404 instead of revealing whether a repository belonging to
    another user actually exists.
    """

    repository = get_repository_metadata(
        owner_sub=owner_sub,
        repo_id=repo_id,
    )

    if repository is None:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    return repository


def list_user_repositories(
    owner_sub: str,
) -> List[Dict[str, Any]]:
    """
    List only repositories owned by one Cognito user.
    """

    response = get_repository_table().query(
        KeyConditionExpression=Key("owner_sub").eq(owner_sub)
    )

    repositories = response.get("Items", [])

    repositories.sort(
        key=lambda repository: repository.get("created_at", ""),
        reverse=True,
    )

    return repositories


def mark_repository_indexed(
    owner_sub: str,
    repo_id: str,
) -> None:
    """
    Mark a repository as successfully indexed.

    "indexed" is a DynamoDB reserved word, so it must be
    referenced through ExpressionAttributeNames.
    """

    get_repository_table().update_item(
        Key={
            "owner_sub": owner_sub,
            "repo_id": repo_id,
        },
        UpdateExpression="SET #indexed = :indexed",
        ExpressionAttributeNames={
            "#indexed": "indexed",
        },
        ExpressionAttributeValues={
            ":indexed": True,
        },
        ConditionExpression=(
            "attribute_exists(owner_sub) "
            "AND attribute_exists(repo_id)"
        ),
    )


def delete_repository_metadata(
    owner_sub: str,
    repo_id: str,
) -> None:
    """
    Remove repository ownership metadata.
    """

    get_repository_table().delete_item(
        Key={
            "owner_sub": owner_sub,
            "repo_id": repo_id,
        }
    )