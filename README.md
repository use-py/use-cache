# Use Cache

一个框架无关的Python缓存库，支持多种后端和框架集成。

## 特性

- 🚀 **框架无关**: 可以与任何Python框架集成，不仅限于FastAPI
- 🔧 **多后端支持**: 支持Redis、Memcached、DynamoDB和内存缓存
- 🎯 **类型安全**: 完整的类型注解支持
- 🔄 **异步优先**: 原生异步支持，同时兼容同步函数
- 🎨 **灵活配置**: 支持自定义编码器、键构建器和过期策略
- 📦 **向后兼容**: 与fastapi-cache完全兼容

## 安装

```bash
# 基础安装
pip install use-cache

# 安装Redis支持
pip install use-cache[redis]

# 安装Memcached支持  
pip install use-cache[memcached]

# 安装DynamoDB支持
pip install use-cache[dynamodb]

# 安装所有后端
pip install use-cache[all]
```

## 快速开始

### 基本使用

```python
import asyncio
from use_cache import CacheManager, InMemoryBackend, JsonCoder

async def main():
    # 初始化缓存管理器
    cache_manager = CacheManager()
    await cache_manager.init(
        backend=InMemoryBackend(),
        coder=JsonCoder(),
        prefix="myapp:",
        expire=300  # 5分钟
    )
    
    # 手动缓存操作
    await cache_manager.set("user:123", {"name": "Alice", "age": 30})
    user = await cache_manager.get("user:123")
    print(user)  # {'name': 'Alice', 'age': 30}

asyncio.run(main())
```

### 装饰器使用

```python
from use_cache import cache, CacheManager, InMemoryBackend, JsonCoder

# 初始化缓存（通常在应用启动时）
async def setup_cache():
    cache_manager = CacheManager()
    await cache_manager.init(
        backend=InMemoryBackend(),
        coder=JsonCoder()
    )

@cache(expire=60)
async def get_user_data(user_id: int):
    # 模拟数据库查询
    return {"id": user_id, "name": f"User {user_id}"}

# 使用
await setup_cache()
user = await get_user_data(123)  # 第一次调用，执行函数
user = await get_user_data(123)  # 第二次调用，使用缓存
```

### FastAPI集成

```python
from fastapi import FastAPI
from use_cache import CacheManager, InMemoryBackend, JsonCoder
from use_cache.integrations.fastapi import cache

app = FastAPI()

@app.on_event("startup")
async def startup():
    cache_manager = CacheManager()
    await cache_manager.init(
        backend=InMemoryBackend(),
        coder=JsonCoder(),
        prefix="api:",
        expire=300
    )

@app.get("/users/{user_id}")
@cache(expire=60)
async def get_user(user_id: int):
    return {"id": user_id, "name": f"User {user_id}"}
```

## 支持的后端

### 内存缓存
```python
from use_cache import InMemoryBackend

backend = InMemoryBackend()
```

### Redis
```python
from use_cache import RedisBackend

# 单个Redis实例
backend = RedisBackend("redis://localhost:6379")

# Redis集群
backend = RedisBackend([
    "redis://node1:6379",
    "redis://node2:6379", 
    "redis://node3:6379"
])
```

### Memcached
```python
from use_cache import MemcachedBackend

backend = MemcachedBackend("127.0.0.1", 11211)
```

### DynamoDB
```python
from use_cache import DynamoDBBackend

backend = DynamoDBBackend(
    table_name="cache_table",
    region_name="us-east-1"
)
```

## 编码器

### JSON编码器（默认）
```python
from use_cache import JsonCoder

coder = JsonCoder()
```

### Pickle编码器
```python
from use_cache import PickleCoder

coder = PickleCoder()
```

### 字符串编码器
```python
from use_cache import StringCoder

coder = StringCoder()
```

## 键构建器

### 默认键构建器
```python
from use_cache import default_key_builder

# 自动根据函数名和参数生成键
```

### 简单键构建器
```python
from use_cache import simple_key_builder

# 仅使用函数名作为键
```

### 自定义键构建器
```python
def custom_key_builder(func, *args, **kwargs):
    return f"custom:{func.__name__}:{hash(str(args) + str(kwargs))}"
```

## 便捷装饰器

```python
from use_cache import cache_one_minute, cache_one_hour, cache_one_day

@cache_one_minute
async def quick_data():
    return "cached for 1 minute"

@cache_one_hour  
async def hourly_data():
    return "cached for 1 hour"

@cache_one_day
async def daily_data():
    return "cached for 1 day"
```

## 开发

### 安装开发依赖
```bash
poetry install --with dev
```

### 运行测试
```bash
poetry run pytest
```

### 运行示例
```bash
# 基本示例
poetry run python examples/basic_usage.py

# FastAPI示例
poetry run python examples/fastapi_example.py
```

## 许可证

MIT License
