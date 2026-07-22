"""Client 模式基础设施 (ADR-024)。

瘦客户端连远端 API：JWT 凭证存储 + ApiClient + 远程代理 service。
零本地算力，backtest run 走提交+轮询。
"""

from ginkgo.client.remote.auth_store import (  # noqa: F401
    AuthRecord,
    auth_path,
    load,
    save,
    clear,
    get_token,
    is_expired,
    ensure_secure_perms,
)
from ginkgo.client.remote.api_client import (  # noqa: F401
    ApiClient,
    ApiError,
    NotLoggedInError,
    TokenExpiredError,
    get_client,
)
from ginkgo.client.remote.services import (  # noqa: F401
    RemoteService,
    RemotePortfolioService,
)
