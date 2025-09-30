"""
use-cache coders for encoding and decoding cached values.
"""
import datetime
import json
import pickle  # nosec:B403
from decimal import Decimal
from typing import Any, Callable, Dict

from .types import Coder

try:
    import pendulum  # type: ignore
except ImportError:
    pendulum = None  # type: ignore


CONVERTERS: Dict[str, Callable[[str], Any]] = {
    "decimal": Decimal,
}

if pendulum is not None:
    CONVERTERS.update({
        "date": lambda x: pendulum.parse(x, exact=True),  # type: ignore
        "datetime": lambda x: pendulum.parse(x, exact=True),  # type: ignore
    })
else:
    CONVERTERS.update({
        "date": lambda x: datetime.datetime.fromisoformat(x).date(),
        "datetime": lambda x: datetime.datetime.fromisoformat(x),
    })


class JsonEncoder(json.JSONEncoder):
    """Custom JSON encoder for special types."""
    
    def default(self, o: Any) -> Any:
        if isinstance(o, datetime.datetime):
            return {"val": o.isoformat(), "_spec_type": "datetime"}
        elif isinstance(o, datetime.date):
            return {"val": o.isoformat(), "_spec_type": "date"}
        elif isinstance(o, Decimal):
            return {"val": str(o), "_spec_type": "decimal"}
        else:
            # Fallback to basic serialization
            try:
                return super().default(o)
            except TypeError:
                return str(o)


def object_hook(obj: Any) -> Any:
    """JSON object hook for deserializing special types."""
    _spec_type = obj.get("_spec_type")
    if not _spec_type:
        return obj

    if _spec_type in CONVERTERS:
        return CONVERTERS[_spec_type](obj["val"])
    else:
        raise TypeError(f"Unknown {_spec_type}")


class JsonCoder(Coder):
    """JSON-based coder for serializing cache values."""
    
    @classmethod
    def encode(cls, value: Any) -> bytes:
        """Encode value to JSON bytes."""
        return json.dumps(value, cls=JsonEncoder).encode()

    @classmethod
    def decode(cls, value: bytes) -> Any:
        """Decode JSON bytes to value."""
        return json.loads(value.decode(), object_hook=object_hook)


class PickleCoder(Coder):
    """Pickle-based coder for serializing cache values."""
    
    @classmethod
    def encode(cls, value: Any) -> bytes:
        """Encode value to pickle bytes."""
        return pickle.dumps(value)

    @classmethod
    def decode(cls, value: bytes) -> Any:
        """Decode pickle bytes to value."""
        return pickle.loads(value)  # noqa: S301


class StringCoder(Coder):
    """Simple string-based coder."""
    
    @classmethod
    def encode(cls, value: Any) -> bytes:
        """Encode value to string bytes."""
        return str(value).encode()

    @classmethod
    def decode(cls, value: bytes) -> str:
        """Decode bytes to string."""
        return value.decode()
