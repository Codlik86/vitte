"""
Serialization utilities for SQLAlchemy models and Python objects
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import InstanceState


def model_to_dict(
    model: Any,
    exclude: Optional[List[str]] = None,
    include_relationships: bool = False
) -> Dict[str, Any]:
    """
    Convert SQLAlchemy model instance to dictionary

    Args:
        model: SQLAlchemy model instance
        exclude: List of field names to exclude
        include_relationships: Whether to include relationship fields

    Returns:
        Dictionary representation of the model

    Usage:
        user = await db.query(User).first()
        user_dict = model_to_dict(user, exclude=['password_hash'])
    """
    if model is None:
        return None

    exclude = exclude or []
    result = {}

    # Get model inspection
    mapper = sa_inspect(model.__class__)

    # Iterate over columns
    for column in mapper.columns:
        if column.key in exclude:
            continue

        value = getattr(model, column.key)

        # Handle special types
        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, bytes):
            value = value.decode('utf-8') if value else None

        result[column.key] = value

    # Include relationships if requested
    if include_relationships:
        for relationship in mapper.relationships:
            if relationship.key in exclude:
                continue

            value = getattr(model, relationship.key)

            # Handle None relationships
            if value is None:
                result[relationship.key] = None
            # Handle list relationships (one-to-many)
            elif isinstance(value, list):
                result[relationship.key] = [
                    model_to_dict(item, exclude=exclude)
                    for item in value
                ]
            # Handle single relationships (many-to-one)
            else:
                result[relationship.key] = model_to_dict(
                    value,
                    exclude=exclude
                )

    return result


def models_to_dict(
    models: List[Any],
    exclude: Optional[List[str]] = None,
    include_relationships: bool = False
) -> List[Dict[str, Any]]:
    """
    Convert list of SQLAlchemy models to list of dictionaries

    Args:
        models: List of SQLAlchemy model instances
        exclude: List of field names to exclude
        include_relationships: Whether to include relationship fields

    Returns:
        List of dictionary representations

    Usage:
        users = await db.query(User).all()
        users_list = models_to_dict(users, exclude=['password_hash'])
    """
    return [
        model_to_dict(model, exclude=exclude, include_relationships=include_relationships)
        for model in models
    ]


def serialize_for_cache(obj: Any) -> Any:
    """
    Serialize Python object for Redis cache storage

    Handles:
    - SQLAlchemy models
    - datetime/date objects
    - Decimal numbers
    - Lists and dicts
    - Primitives

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable representation
    """
    # Handle None
    if obj is None:
        return None

    # Handle primitives
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # Handle datetime
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # Handle Decimal
    if isinstance(obj, Decimal):
        return float(obj)

    # Handle bytes
    if isinstance(obj, bytes):
        return obj.decode('utf-8')

    # Handle SQLAlchemy models
    if hasattr(obj, '__table__'):
        return model_to_dict(obj)

    # Handle lists
    if isinstance(obj, (list, tuple)):
        return [serialize_for_cache(item) for item in obj]

    # Handle dicts
    if isinstance(obj, dict):
        return {
            key: serialize_for_cache(value)
            for key, value in obj.items()
        }

    # For other objects, try to get __dict__
    if hasattr(obj, '__dict__'):
        return serialize_for_cache(obj.__dict__)

    # Fallback to string representation
    return str(obj)


def get_model_cache_key(model_class: Any, model_id: Any) -> str:
    """
    Generate cache key for SQLAlchemy model

    Args:
        model_class: SQLAlchemy model class (e.g., User)
        model_id: Model primary key value

    Returns:
        Cache key string like 'user:123'

    Usage:
        key = get_model_cache_key(User, 123)  # Returns "user:123"
    """
    table_name = model_class.__tablename__
    return f"{table_name}:{model_id}"


def get_model_pattern(model_class: Any) -> str:
    """
    Get cache key pattern for all instances of model

    Args:
        model_class: SQLAlchemy model class

    Returns:
        Pattern string like 'user:*'

    Usage:
        pattern = get_model_pattern(User)  # Returns "user:*"
        await redis_client.delete_pattern(pattern)  # Delete all user caches
    """
    table_name = model_class.__tablename__
    return f"{table_name}:*"
