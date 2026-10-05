"""OpenAPI request bodies for bounded raw media uploads."""


def _binary_body(media_type: str, description: str) -> dict:
    return {
        "requestBody": {
            "required": True,
            "description": description,
            "content": {
                media_type: {
                    "schema": {"type": "string", "format": "binary"},
                },
            },
        },
    }


def binary_upload_openapi() -> dict:
    """Describe raw octet-stream requests consumed by the bounded upload adapter."""

    return _binary_body(
        "application/octet-stream",
        "Raw file bytes; the server streams them directly into encrypted storage.",
    )


def video_binary_upload_openapi(
    *, profile_required: bool = False, include_blur_strength: bool = False
) -> dict:
    """Document the video format and optional privacy/model-input headers."""

    parameters = [
        {
            "name": "X-Video-Format",
            "in": "header",
            "required": True,
            "description": "Container extension used to assign a neutral server-side filename.",
            "schema": {"type": "string", "enum": ["avi", "mp4", "mov", "webm"]},
        },
    ]
    if profile_required:
        parameters.append(
            {
                "name": "X-Video-Profile",
                "in": "header",
                "required": True,
                "description": "Reviewed video privacy transform profile.",
                "schema": {
                    "type": "string",
                    "enum": ["face-redacted", "face-redacted-pose-preview"],
                },
            }
        )
    if include_blur_strength:
        parameters.append(
            {
                "name": "X-Model-Blur-Percent",
                "in": "header",
                "required": False,
                "description": "VSViG model-input blur as a percentage of the reviewed default sigma. Values below 50 are rejected.",
                "schema": {
                    "type": "integer",
                    "minimum": 50,
                    "maximum": 100,
                    "default": 100,
                },
            }
        )
    operation = binary_upload_openapi()
    operation["parameters"] = parameters
    return operation


def pdf_upload_openapi() -> dict:
    """Describe a bounded raw PDF request body."""

    return _binary_body("application/pdf", "Raw PDF source-report bytes.")
