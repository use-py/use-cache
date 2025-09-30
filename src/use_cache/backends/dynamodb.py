"""
DynamoDB cache backend implementation.
"""
import datetime
from typing import TYPE_CHECKING, Optional, Tuple

from ..types import Backend

try:
    from aiobotocore.client import AioBaseClient  # type: ignore
    from aiobotocore.session import AioSession, get_session  # type: ignore
    _dynamodb_available = True
    
    if TYPE_CHECKING:
        from types_aiobotocore_dynamodb import DynamoDBClient  # type: ignore
    else:
        DynamoDBClient = AioBaseClient
        
except ImportError:
    AioBaseClient = None  # type: ignore
    AioSession = None  # type: ignore
    get_session = None  # type: ignore
    DynamoDBClient = None  # type: ignore
    _dynamodb_available = False


class DynamoDBBackend(Backend):
    """
    Amazon DynamoDB backend provider.

    This backend requires an existing table within your AWS environment to be passed during
    backend init. If TTL is going to be used, this needs to be manually enabled on the table
    using the `ttl` key. DynamoDB will take care of deleting outdated objects, but this is not
    instant so don't be alarmed when they linger around for a bit.

    As with all AWS clients, credentials will be taken from the environment. Check the AWS SDK
    for more information.

    Usage:
        >> dynamodb = DynamoDBBackend(table_name="your-cache", region="eu-west-1")
        >> await dynamodb.init()
        >> cache_manager.init(dynamodb)
    """

    def __init__(self, table_name: str, region: Optional[str] = None) -> None:
        if not _dynamodb_available:
            raise ImportError(
                "aiobotocore is not available. Install with: pip install aiobotocore[dynamodb]"
            )
        
        self.session: "AioSession" = get_session()  # type: ignore
        self.table_name = table_name
        self.region = region
        self.client: Optional["DynamoDBClient"] = None

    async def init(self) -> None:
        """Initialize the DynamoDB client."""
        if self.client is None:
            self.client = await self.session.create_client(  # type: ignore
                "dynamodb", region_name=self.region
            ).__aenter__()

    async def close(self) -> None:
        """Close the DynamoDB client."""
        if self.client is not None:
            await self.client.__aexit__(None, None, None)
            self.client = None

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        """Get value with TTL. Returns (ttl_seconds, value)."""
        if self.client is None:
            await self.init()
            
        response = await self.client.get_item(  # type: ignore
            TableName=self.table_name, Key={"key": {"S": key}}
        )

        if "Item" in response:
            value = response["Item"].get("value", {}).get("B")
            ttl = response["Item"].get("ttl", {}).get("N")

            if not ttl:
                return -1, value

            # It's only eventually consistent so we need to check ourselves
            expire = int(ttl) - int(datetime.datetime.now().timestamp())
            if expire > 0:
                return expire, value

        return 0, None

    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key."""
        if self.client is None:
            await self.init()
            
        response = await self.client.get_item(  # type: ignore
            TableName=self.table_name, Key={"key": {"S": key}}
        )
        if "Item" in response:
            return response["Item"].get("value", {}).get("B")
        return None

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        """Set value with optional expiration."""
        if self.client is None:
            await self.init()
            
        ttl = (
            {
                "ttl": {
                    "N": str(
                        int(
                            (
                                datetime.datetime.now() + datetime.timedelta(seconds=expire)
                            ).timestamp()
                        )
                    )
                }
            }
            if expire
            else {}
        )

        await self.client.put_item(  # type: ignore
            TableName=self.table_name,
            Item={
                **{
                    "key": {"S": key},
                    "value": {"B": value},
                },
                **ttl,
            },
        )

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        """Clear cache by specific key. Namespace clearing is not efficiently supported."""
        if namespace:
            raise NotImplementedError("DynamoDB doesn't efficiently support namespace-based clearing")
        elif key:
            if self.client is None:
                await self.init()
            await self.client.delete_item(  # type: ignore
                TableName=self.table_name, Key={"key": {"S": key}}
            )
            return 1
        return 0