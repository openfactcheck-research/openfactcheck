"""Resolve a user's stored secrets for a cloud pipeline run.

The engine runs on behalf of one user. To reach the LLM and search providers,
it needs that user's API keys, which the API stores encrypted in the users
table. This reads the user's encrypted secrets and KMS-decrypts them into an
environment-variable map, the shape the chat layer reads its keys from.

The DynamoDB key layout (``USER#<id>`` / ``SECRET#<name>``) and the
base64-KMS-ciphertext format mirror how the API writes secrets. The engine
reimplements only the read-and-decrypt half so it stays free of any ``api``
import, consistent with shipping as its own container.
"""

import base64
import os

# Sort-key prefix marking a user's secret items; mirrors the API storage layout.
_SECRET_PREFIX = "SECRET#"  # noqa: S105 - sort-key prefix, not a credential.


def resolve_user_secrets(user_id: str) -> dict[str, str]:
    """Return the user's secrets as ``{env_var_name: value}``, decrypting via KMS.

    Reads the table name, region, and KMS key id from the environment. Returns
    an empty map when the user has stored no secrets.
    """
    import boto3  # noqa: PLC0415 - lazy import for the optional cloud dependency.

    table_name = os.environ["OPENFACTCHECK_DYNAMODB_USERS_TABLE_NAME"]
    region = os.environ.get("OPENFACTCHECK_DYNAMODB_REGION", "us-east-1")
    key_id = os.environ["OPENFACTCHECK_SECRETS_KMS_KEY_ID"]

    table = boto3.resource("dynamodb", region_name=region).Table(table_name)
    kms = boto3.client("kms", region_name=region)

    response = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
        ExpressionAttributeValues={":pk": f"USER#{user_id}", ":prefix": _SECRET_PREFIX},
    )

    secrets: dict[str, str] = {}
    for item in response.get("Items", []):
        name = item.get("name")
        ciphertext = item.get("ciphertext")
        if not isinstance(name, str) or not isinstance(ciphertext, str):
            continue
        decrypted = kms.decrypt(CiphertextBlob=base64.b64decode(ciphertext), KeyId=key_id)
        secrets[name] = decrypted["Plaintext"].decode()
    return secrets
