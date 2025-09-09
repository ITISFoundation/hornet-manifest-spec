from typing import Any


def validate_metadata_manually(metadata: dict[str, Any]) -> dict[str, Any]:
    """Manually validate metadata structure without Pydantic."""
    required_fields = ["name", "version", "description"]  # Adjust based on your Metadata model
    
    # Check required fields exist
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Missing required field: {field}")
    
    # Type validation examples (adjust based on your actual Metadata model)
    if not isinstance(metadata.get("name"), str):
        raise TypeError("Field 'name' must be a string")
    
    if not isinstance(metadata.get("version"), str):
        raise TypeError("Field 'version' must be a string")
    
    if not isinstance(metadata.get("description"), str):
        raise TypeError("Field 'description' must be a string")
    
    # Add more specific validations as needed
    return metadata
