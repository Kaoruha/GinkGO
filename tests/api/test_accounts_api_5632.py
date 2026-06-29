"""#5632: Account 创建 schema 字段名与直觉不符。

表象: 用户用直觉命名 `broker`/`account_name` POST 创建账户 → 422 missing `exchange`/`name`。
根因: `CreateLiveAccountRequest`/`UpdateLiveAccountRequest` 字段无 alias 兼容直觉命名,
      且 Pydantic extra="ignore" 静默丢弃 `broker`/`account_name` → 必填 `exchange`/`name` missing。
契约:
  - 输入接受 `exchange`/`broker` 任一(主名 exchange 不变,DB/前端契约不破坏);
  - 输入接受 `name`/`account_name` 任一;
  - OpenAPI schema 含字段 description,消除命名歧义。
"""

from pydantic import ValidationError


def test_create_accepts_intuitive_aliases(api_modules):
    """#5632: broker/account_name 别名输入应被接受(用户直觉命名)。"""
    from models.accounts import CreateLiveAccountRequest

    req = CreateLiveAccountRequest(
        broker="okx", account_name="test", api_key="k", api_secret="s"
    )
    assert req.exchange.value == "okx"
    assert req.name == "test"


def test_create_still_accepts_canonical_names(api_modules):
    """#5632: 加 alias 后主名 exchange/name 仍工作(向后兼容,DB/前端契约不破坏)。"""
    from models.accounts import CreateLiveAccountRequest

    req = CreateLiveAccountRequest(
        exchange="binance", name="canonical", api_key="k", api_secret="s"
    )
    assert req.exchange.value == "binance"
    assert req.name == "canonical"


def test_openapi_schema_has_field_descriptions(api_modules):
    """#5632: OpenAPI schema 字段含 description,消除命名歧义。"""
    from models.accounts import CreateLiveAccountRequest

    schema = CreateLiveAccountRequest.model_json_schema()
    props = schema["properties"]
    assert props["exchange"].get("description"), "exchange 缺 description"
    assert props["name"].get("description"), "name 缺 description"


def test_update_accepts_account_name_alias(api_modules):
    """#5632: UpdateLiveAccountRequest.name 也接受 account_name 别名。"""
    from models.accounts import UpdateLiveAccountRequest

    req = UpdateLiveAccountRequest(account_name="renamed")
    assert req.name == "renamed"
