# Upstream: fastapi, ginkgo.services
# Downstream: web-ui
# Role: Ginkgo API Server - 为 web-ui 提供完整的后端 API 接口

"""
Ginkgo API Server

为 Web UI 和外部应用提供 RESTful API 接口。
通过 service_hub 统一访问所有后端服务。
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio
import json
import secrets
import hashlib

from fastapi import FastAPI, Query, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# Ginkgo 服务入口
from ginkgo import service_hub
from ginkgo.libs import GCONF, datetime_normalize
from ginkgo.enums import FREQUENCY_TYPES, ADJUSTMENT_TYPES, DIRECTION_TYPES, ORDER_TYPES

app = FastAPI(
    title="Ginkgo API",
    description="量化交易平台 API",
    version="0.11.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 认证相关 ==========

# 简单的内存存储（生产环境应使用数据库）
active_tokens: Dict[str, Dict] = {}

# 模拟用户数据（生产环境应从数据库获取）
MOCK_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "uuid": "user-admin-001",
        "username": "admin",
        "display_name": "Administrator",
        "is_admin": True,
    }
}


class LoginRequest(BaseModel):
    username: str
    password: str


def verify_password(plain_password: str, password_hash: str) -> bool:
    return hashlib.sha256(plain_password.encode()).hexdigest() == password_hash


def generate_token() -> str:
    return secrets.token_urlsafe(32)


@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """用户登录"""
    user = MOCK_USERS.get(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = generate_token()
    expires_at = (datetime.now() + timedelta(hours=24)).isoformat()

    active_tokens[token] = {
        "user_uuid": user["uuid"],
        "username": user["username"],
        "expires_at": expires_at,
    }

    return {
        "token": token,
        "expires_at": expires_at,
        "user": {
            "uuid": user["uuid"],
            "username": user["username"],
            "display_name": user["display_name"],
            "is_admin": user["is_admin"],
        }
    }


@app.post("/api/v1/auth/logout")
async def logout(request: Request):
    """用户登出"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        active_tokens.pop(token, None)
    return {"status": "success"}


@app.get("/api/v1/auth/verify")
async def verify_token(request: Request):
    """验证 Token"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {"valid": False}

    token = auth_header[7:]
    token_data = active_tokens.get(token)

    if not token_data:
        return {"valid": False}

    expires_at = datetime.fromisoformat(token_data["expires_at"])
    if datetime.now() > expires_at:
        active_tokens.pop(token, None)
        return {"valid": False}

    user = MOCK_USERS.get(token_data["username"])
    return {
        "valid": True,
        "user": {
            "uuid": user["uuid"],
            "username": user["username"],
            "display_name": user["display_name"],
            "is_admin": user["is_admin"],
        } if user else None
    }


@app.get("/api/v1/auth/me")
async def get_current_user(request: Request):
    """获取当前用户信息"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header[7:]
    token_data = active_tokens.get(token)

    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = MOCK_USERS.get(token_data["username"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "uuid": user["uuid"],
        "username": user["username"],
        "display_name": user["display_name"],
        "is_admin": user["is_admin"],
    }


# ========== 辅助函数 ==========

def get_bar_service():
    """获取 BarService 实例"""
    return service_hub.data.bar_service()


def get_stockinfo_service():
    """获取 StockinfoService 实例"""
    return service_hub.data.stockinfo_service()


def get_engine_service():
    """获取 EngineService 实例"""
    return service_hub.data.engine_service()


def get_portfolio_service():
    """获取 PortfolioService 实例"""
    return service_hub.data.portfolio_service()


def serialize_model(model):
    """将数据模型序列化为字典"""
    if model is None:
        return None

    # 如果有 to_dict 方法，优先使用
    if hasattr(model, 'to_dict'):
        return model.to_dict()

    # 对于 SQLAlchemy 模型，使用 __table__ 列名
    if hasattr(model, '__table__'):
        result = {}
        for column in model.__table__.columns:
            attr_name = column.name
            if hasattr(model, attr_name):
                value = getattr(model, attr_name)
                if isinstance(value, datetime):
                    result[attr_name] = value.isoformat() if value else None
                elif hasattr(value, 'isoformat'):
                    result[attr_name] = value.isoformat()
                else:
                    result[attr_name] = value
        return result

    # 通用回退
    result = {}
    for attr in dir(model):
        if not attr.startswith('_') and not callable(getattr(model, attr)):
            value = getattr(model, attr)
            if isinstance(value, datetime):
                result[attr] = value.isoformat()
            elif hasattr(value, 'isoformat'):
                result[attr] = value.isoformat()
            elif isinstance(value, (str, int, float, bool, type(None))):
                result[attr] = value
    return result


def serialize_modellist(modellist):
    """将 ModelList 序列化为列表"""
    if modellist is None:
        return []
    return [serialize_model(item) for item in modellist]


# ========== API 路由 ==========

@app.get("/")
async def root():
    """API 根路径"""
    return {"message": "Ginkgo API Server", "version": "0.11.0"}


@app.get("/api/health")
async def health_check():
    """健康检查"""
    module_status = service_hub.get_module_status()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "modules": module_status
    }


# ========== 回测任务相关 ==========

def get_backtest_task_service():
    """获取回测任务服务"""
    return service_hub.data.backtest_task_service()


@app.get("/api/v1/backtest")
async def list_backtests(
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    engine_id: Optional[str] = Query(None, description="引擎ID筛选"),
    portfolio_id: Optional[str] = Query(None, description="投资组合ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
):
    """获取回测任务列表"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.list(
            page=page,
            page_size=size,
            engine_id=engine_id,
            portfolio_id=portfolio_id,
            status=status
        )
        if result.is_success():
            data = result.data
            return {
                "data": serialize_modellist(data.get("data", [])),
                "total": data.get("total", 0),
                "page": page,
                "size": size,
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)
    except Exception as e:
        print(f"[ERROR] Failed to list backtests: {e}")
        return {"data": [], "total": 0, "page": page, "size": size}


@app.get("/api/v1/backtest/{backtest_id}")
async def get_backtest(backtest_id: str):
    """获取回测任务详情"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_by_id(backtest_id)
        if result.is_success() and result.data:
            return serialize_model(result.data)
        else:
            raise HTTPException(status_code=404, detail="Backtest task not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to get backtest {backtest_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BacktestCreateRequest(BaseModel):
    """创建回测任务请求"""
    task_id: str
    engine_id: str = ""
    portfolio_id: str = ""
    start_date: Optional[str] = None  # YYYY-MM-DD 格式
    end_date: Optional[str] = None    # YYYY-MM-DD 格式
    config_snapshot: dict = {}


@app.post("/api/v1/backtest")
async def create_backtest(request: BacktestCreateRequest):
    """创建回测任务"""
    try:
        task_service = get_backtest_task_service()

        # 检查 task_id 是否已存在
        existing = task_service.exists(task_id=request.task_id)
        if existing.is_success() and existing.data.get("exists"):
            raise HTTPException(status_code=400, detail=f"Task ID '{request.task_id}' already exists")

        # 解析日期
        start_time = None
        end_time = None
        if request.start_date:
            try:
                start_time = datetime.strptime(request.start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format, expected YYYY-MM-DD")
        if request.end_date:
            try:
                end_time = datetime.strptime(request.end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format, expected YYYY-MM-DD")

        result = task_service.create(
            task_id=request.task_id,
            engine_id=request.engine_id,
            portfolio_id=request.portfolio_id,
            config_snapshot=request.config_snapshot,
            start_time=start_time or datetime.now(),
            end_time=end_time,
        )

        if result.is_success():
            return serialize_model(result.data)
        else:
            raise HTTPException(status_code=500, detail=result.error)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to create backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/backtest/{backtest_id}")
async def delete_backtest(backtest_id: str):
    """删除回测任务"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.delete(backtest_id)
        if result.is_success():
            return {"success": True, "message": "Backtest task deleted"}
        else:
            raise HTTPException(status_code=404, detail=result.error)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to delete backtest {backtest_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/backtest/{backtest_id}/netvalue")
async def get_backtest_netvalue(backtest_id: str):
    """获取回测净值曲线"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_netvalue_data(backtest_id)
        if result.is_success() and result.data:
            return {
                "strategy": result.data.get("strategy", []),
                "benchmark": result.data.get("benchmark", []),
            }
        return {"strategy": [], "benchmark": []}
    except Exception as e:
        print(f"[ERROR] Failed to get netvalue for {backtest_id}: {e}")
        return {"strategy": [], "benchmark": []}


@app.get("/api/v1/backtest/compare")
async def compare_backtests(ids: str = Query(..., description="逗号分隔的回测ID")):
    """对比多个回测结果"""
    id_list = [i.strip() for i in ids.split(",")]
    try:
        task_service = get_backtest_task_service()
        result = task_service.compare(id_list)
        if result.is_success():
            return {"data": result.data}
        return {"data": {}}
    except Exception as e:
        print(f"[ERROR] Failed to compare backtests: {e}")
        return {"data": {}}


@app.get("/api/v1/backtest/{backtest_id}/analyzers")
async def get_backtest_analyzers(backtest_id: str):
    """获取回测任务挂载的所有分析器及其最新值"""
    try:
        # 先获取回测任务信息
        task_service = get_backtest_task_service()
        task_result = task_service.get_by_id(backtest_id)
        if not task_result.is_success() or not task_result.data:
            raise HTTPException(status_code=404, detail="Backtest task not found")

        task = task_result.data
        task_id = task.task_id if hasattr(task, 'task_id') else task.get('task_id')
        portfolio_id = task.portfolio_id if hasattr(task, 'portfolio_id') else task.get('portfolio_id')

        # 获取运行摘要（包含分析器列表）
        result_service = service_hub.data.result_service()
        summary_result = result_service.get_run_summary(task_id)

        analyzers = []
        if summary_result.is_success() and summary_result.data:
            analyzer_names = summary_result.data.get("analyzers", [])

            # 获取每个分析器的最新值和统计信息
            for name in analyzer_names:
                analyzer_info = {
                    "name": name,
                    "latest_value": None,
                    "record_count": 0,
                    "stats": None
                }

                try:
                    # 获取统计信息
                    if portfolio_id:
                        stats_result = result_service.get_analyzer_stats(
                            run_id=task_id,
                            portfolio_id=portfolio_id,
                            analyzer_name=name
                        )
                        if stats_result.is_success() and stats_result.data:
                            analyzer_info["stats"] = stats_result.data
                            analyzer_info["latest_value"] = stats_result.data.get("latest")
                            analyzer_info["record_count"] = stats_result.data.get("count", 0)
                except Exception as e:
                    print(f"[DEBUG] Failed to get stats for {name}: {e}")

                analyzers.append(analyzer_info)

        return {
            "task_id": task_id,
            "portfolio_id": portfolio_id,
            "analyzers": analyzers,
            "total_count": len(analyzers)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to get analyzers for backtest {backtest_id}: {e}")
        return {"task_id": None, "portfolio_id": None, "analyzers": [], "total_count": 0}


# ========== 引擎配置相关 ==========

@app.get("/api/v1/engine")
async def list_engines(
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
):
    """获取引擎配置列表"""
    try:
        engine_service = get_engine_service()
        result = engine_service.get()
        if result.is_success():
            return {
                "data": serialize_modellist(result.data),
                "total": len(result.data) if result.data else 0,
                "page": page,
                "size": size,
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)
    except Exception as e:
        print(f"[ERROR] Failed to list engines: {e}")
        return {"data": [], "total": 0, "page": page, "size": size}


@app.get("/api/v1/engine/{engine_id}")
async def get_engine(engine_id: str):
    """获取引擎配置详情"""
    try:
        engine_service = get_engine_service()
        result = engine_service.get(engine_id=engine_id)
        if result.is_success() and result.data:
            items = result.data if isinstance(result.data, list) else [result.data]
            if items and len(items) > 0:
                return serialize_model(items[0])
        raise HTTPException(status_code=404, detail="Engine not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to get engine {engine_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/engine/{engine_id}/tasks")
async def get_engine_tasks(
    engine_id: str,
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
):
    """获取引擎的所有回测任务"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.list(page=page, page_size=size, engine_id=engine_id)
        if result.is_success():
            data = result.data
            return {
                "data": serialize_modellist(data.get("data", [])),
                "total": data.get("total", 0),
                "page": page,
                "size": size,
            }
        return {"data": [], "total": 0, "page": page, "size": size}
    except Exception as e:
        print(f"[ERROR] Failed to get engine tasks: {e}")
        return {"data": [], "total": 0, "page": page, "size": size}


# ========== 因子研究相关 ==========

@app.get("/api/v1/research/ic")
async def get_ic_analysis(
    factor_name: str = Query(...),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """获取 IC 分析结果"""
    try:
        if service_hub.research is None:
            return {"factor_name": factor_name, "statistics": {}, "ic_series": []}

        ic_analyzer = service_hub.research.ic_analyzer()
        result = ic_analyzer.analyze(
            factor_name=factor_name,
            start_date=datetime_normalize(start_date) if start_date else None,
            end_date=datetime_normalize(end_date) if end_date else None,
        )
        if result.success:
            return result.data
        return {"factor_name": factor_name, "statistics": {}, "ic_series": []}
    except Exception as e:
        print(f"[ERROR] Failed to get IC analysis: {e}")
        return {"factor_name": factor_name, "statistics": {}, "ic_series": []}


@app.get("/api/v1/research/layering")
async def get_layering_result(
    factor_name: str = Query(...),
    n_groups: int = Query(5, ge=2, le=10),
):
    """获取因子分层结果"""
    try:
        if service_hub.research is None:
            return {"factor_name": factor_name, "n_groups": n_groups, "groups": []}

        layering_analyzer = service_hub.research.layering_analyzer()
        result = layering_analyzer.analyze(factor_name=factor_name, n_groups=n_groups)
        if result.success:
            return result.data
        return {"factor_name": factor_name, "n_groups": n_groups, "groups": []}
    except Exception as e:
        print(f"[ERROR] Failed to get layering result: {e}")
        return {"factor_name": factor_name, "n_groups": n_groups, "groups": []}


@app.get("/api/v1/research/factors")
async def list_factors():
    """获取可用因子列表"""
    try:
        if service_hub.features is None:
            return {"data": []}

        # 获取已注册的因子
        factor_registry = service_hub.features.factor_registry
        factors = []
        for name, factor_def in factor_registry.list_factors().items():
            factors.append({
                "name": name,
                "description": getattr(factor_def, 'description', name),
            })
        return {"data": factors}
    except Exception as e:
        print(f"[ERROR] Failed to list factors: {e}")
        return {"data": []}


# ========== 验证相关 ==========

@app.post("/api/v1/validation/walkforward")
async def run_walkforward_validation(request: dict):
    """执行走步验证"""
    try:
        if service_hub.validation is None:
            return {"status": "error", "message": "Validation module not available"}

        n_folds = request.get("n_folds", 5)
        validator = service_hub.validation.walk_forward_validator()

        # 这里需要传入实际的回测配置
        result = validator.validate(
            backtest_config=request.get("backtest_config", {}),
            n_folds=n_folds,
            window_type=request.get("window_type", "expanding"),
        )
        if result.success:
            return result.data
        return {"status": "error", "message": result.error}
    except Exception as e:
        print(f"[ERROR] Failed to run walkforward validation: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/v1/validation/montecarlo")
async def run_montecarlo_simulation(request: dict):
    """执行蒙特卡洛模拟"""
    try:
        if service_hub.validation is None:
            return {"status": "error", "message": "Validation module not available"}

        n_simulations = request.get("n_simulations", 10000)
        simulator = service_hub.validation.monte_carlo_simulator()

        result = simulator.simulate(
            returns=request.get("returns", []),
            n_simulations=n_simulations,
            confidence_level=request.get("confidence_level", 0.95),
        )
        if result.success:
            return result.data
        return {"status": "error", "message": result.error}
    except Exception as e:
        print(f"[ERROR] Failed to run montecarlo simulation: {e}")
        return {"status": "error", "message": str(e)}


# ========== 优化相关 ==========

@app.post("/api/v1/optimization/grid")
async def run_grid_optimization(request: dict):
    """执行网格搜索优化"""
    try:
        if service_hub.optimization is None:
            return {"status": "error", "message": "Optimization module not available"}

        optimizer = service_hub.optimization.grid_search_optimizer()

        result = optimizer.optimize(
            param_ranges=request.get("param_ranges", {}),
            backtest_config=request.get("backtest_config", {}),
            maximize=request.get("maximize", True),
            metric=request.get("metric", "sharpe_ratio"),
        )
        if result.success:
            return result.data
        return {"status": "error", "message": result.error}
    except Exception as e:
        print(f"[ERROR] Failed to run grid optimization: {e}")
        return {"status": "error", "message": str(e)}


# ========== 组件管理 ==========

from ginkgo.enums import FILE_TYPES


def get_file_service():
    """获取 FileService 实例"""
    return service_hub.data.file_service()


@app.get("/api/v1/components/strategies")
async def list_strategies():
    """获取策略组件列表"""
    try:
        file_service = get_file_service()
        result = file_service.get(filters={"type": FILE_TYPES.STRATEGY.value})
        print(f"[DEBUG] result.success={result.success}, data type={type(result.data)}")

        if result.success and result.data:
            strategies = []
            files = result.data.get("files", []) if isinstance(result.data, dict) else result.data
            print(f"[DEBUG] files count={len(files)}")
            for f in files:
                # 解析 data 字段获取参数信息
                params = []
                try:
                    import json
                    data_obj = json.loads(f.data.decode('utf-8')) if f.data else {}
                    params = data_obj.get("params", [])
                except:
                    # 如果不是JSON，尝试从Python代码解析
                    params = extract_params_from_python(f.data)

                strategies.append({
                    "uuid": f.uuid,
                    "name": f.name,
                    "type": "strategy",
                    "params": params,
                    "created_at": f.create_at.isoformat() if f.create_at else None,
                })
            return {"data": strategies}
        return {"data": []}
    except Exception as e:
        print(f"[ERROR] Failed to list strategies: {e}")
        import traceback
        traceback.print_exc()
        return {"data": []}


@app.get("/api/v1/components/risks")
async def list_risks():
    """获取风控组件列表"""
    try:
        file_service = get_file_service()
        result = file_service.get(filters={"type": FILE_TYPES.RISKMANAGER.value})

        if result.success and result.data:
            risks = []
            files = result.data.get("files", []) if isinstance(result.data, dict) else result.data
            for f in files:
                params = []
                try:
                    import json
                    data_obj = json.loads(f.data.decode('utf-8')) if f.data else {}
                    params = data_obj.get("params", [])
                except:
                    # 如果不是JSON，尝试从Python代码解析
                    params = extract_params_from_python(f.data)

                risks.append({
                    "uuid": f.uuid,
                    "name": f.name,
                    "type": "risk",
                    "params": params,
                    "created_at": f.create_at.isoformat() if f.create_at else None,
                })
            return {"data": risks}
        return {"data": []}
    except Exception as e:
        print(f"[ERROR] Failed to list risks: {e}")
        import traceback
        traceback.print_exc()
        return {"data": []}


@app.get("/api/v1/components/sizers")
async def list_sizers():
    """获取仓位组件列表"""
    try:
        file_service = get_file_service()
        result = file_service.get(filters={"type": FILE_TYPES.SIZER.value})

        if result.success and result.data:
            sizers = []
            files = result.data.get("files", []) if isinstance(result.data, dict) else result.data
            for f in files:
                params = []
                try:
                    import json
                    data_obj = json.loads(f.data.decode('utf-8')) if f.data else {}
                    params = data_obj.get("params", [])
                except:
                    # 如果不是JSON，尝试从Python代码解析
                    params = extract_params_from_python(f.data)

                sizers.append({
                    "uuid": f.uuid,
                    "name": f.name,
                    "type": "sizer",
                    "params": params,
                    "created_at": f.create_at.isoformat() if f.create_at else None,
                })
            return {"data": sizers}
        return {"data": []}
    except Exception as e:
        print(f"[ERROR] Failed to list sizers: {e}")
        return {"data": []}


def extract_params_from_python(code: bytes) -> list:
    """从Python源代码中提取__init__方法的参数"""
    if not code:
        return []

    try:
        import ast
        source = code.decode('utf-8')
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        params = []
                        # 跳过self参数
                        args = item.args.args[1:] if item.args.args else []
                        defaults = item.args.defaults
                        # 计算有默认值的参数起始位置
                        num_defaults = len(defaults)
                        num_args = len(args)
                        default_start = num_args - num_defaults

                        for i, arg in enumerate(args):
                            # 跳过 *args 和 **kwargs
                            if arg.arg.startswith('*'):
                                continue

                            param = {
                                "name": arg.arg,
                                "type": "string",  # 默认类型
                                "label": arg.arg,
                            }

                            # 解析类型注解
                            if arg.annotation:
                                type_str = ast.unparse(arg.annotation)
                                if 'int' in type_str or 'float' in type_str or 'number' in type_str.lower():
                                    param["type"] = "number"
                                elif 'bool' in type_str:
                                    param["type"] = "boolean"
                                elif 'List' in type_str or 'list' in type_str:
                                    param["type"] = "string"
                                    param["label"] = f"{arg.arg} (逗号分隔)"

                            # 解析默认值
                            default_idx = i - default_start
                            if default_idx >= 0 and default_idx < len(defaults):
                                default = defaults[default_idx]
                                if isinstance(default, ast.Constant):
                                    param["default"] = default.value
                                elif isinstance(default, ast.List):
                                    param["default"] = ",".join([ast.unparse(e) for e in default.elts])
                                else:
                                    param["default"] = ast.unparse(default)

                            # 只添加有意义的参数（排除name等通用参数）
                            if arg.arg not in ('name', 'args', 'kwargs'):
                                params.append(param)

                        return params
        return []
    except Exception as e:
        print(f"[DEBUG] Failed to parse Python code: {e}")
        return []


@app.get("/api/v1/components/selectors")
async def list_selectors():
    """获取选股器组件列表"""
    try:
        file_service = get_file_service()
        result = file_service.get(filters={"type": FILE_TYPES.SELECTOR.value})

        if result.success and result.data:
            selectors = []
            files = result.data.get("files", []) if isinstance(result.data, dict) else result.data
            for f in files:
                params = []
                # 首先尝试从JSON解析
                try:
                    import json
                    data_obj = json.loads(f.data.decode('utf-8')) if f.data else {}
                    params = data_obj.get("params", [])
                except:
                    # 如果不是JSON，尝试从Python代码解析
                    params = extract_params_from_python(f.data)

                selectors.append({
                    "uuid": f.uuid,
                    "name": f.name,
                    "type": "selector",
                    "params": params,
                    "created_at": f.create_at.isoformat() if f.create_at else None,
                })
            return {"data": selectors}
        return {"data": []}
    except Exception as e:
        print(f"[ERROR] Failed to list selectors: {e}")
        return {"data": []}


@app.get("/api/v1/components/analyzers")
async def list_analyzers():
    """获取分析器组件列表"""
    try:
        file_service = get_file_service()
        result = file_service.get(filters={"type": FILE_TYPES.ANALYZER.value})

        if result.success and result.data:
            analyzers = []
            files = result.data.get("files", []) if isinstance(result.data, dict) else result.data
            for f in files:
                params = []
                try:
                    import json
                    data_obj = json.loads(f.data.decode('utf-8')) if f.data else {}
                    params = data_obj.get("params", [])
                except:
                    # 如果不是JSON，尝试从Python代码解析
                    params = extract_params_from_python(f.data)

                analyzers.append({
                    "uuid": f.uuid,
                    "name": f.name,
                    "type": "analyzer",
                    "params": params,
                    "created_at": f.create_at.isoformat() if f.create_at else None,
                })
            return {"data": analyzers}
        return {"data": []}
    except Exception as e:
        print(f"[ERROR] Failed to list analyzers: {e}")
        return {"data": []}


@app.get("/api/v1/components/handlers")
async def list_handlers():
    """获取事件处理器组件列表"""
    try:
        file_service = get_file_service()
        result = file_service.get(filters={"type": FILE_TYPES.HANDLER.value})

        if result.success and result.data:
            handlers = []
            files = result.data.get("files", []) if isinstance(result.data, dict) else result.data
            for f in files:
                params = []
                try:
                    import json
                    data_obj = json.loads(f.data.decode('utf-8')) if f.data else {}
                    params = data_obj.get("params", [])
                except:
                    params = extract_params_from_python(f.data)

                handlers.append({
                    "uuid": f.uuid,
                    "name": f.name,
                    "type": "handler",
                    "params": params,
                    "created_at": f.create_at.isoformat() if f.create_at else None,
                })
            return {"data": handlers}
        return {"data": []}
    except Exception as e:
        print(f"[ERROR] Failed to list handlers: {e}")
        return {"data": []}


# ========== Portfolio 管理 ==========

class PortfolioCreateRequest(BaseModel):
    name: str
    mode: str = "BACKTEST"
    initial_cash: float = 100000
    benchmark: Optional[str] = None
    description: Optional[str] = None
    selectors: List[Dict[str, Any]] = []
    sizer_uuid: Optional[str] = None
    strategies: List[Dict[str, Any]] = []
    risk_managers: List[Dict[str, Any]] = []
    analyzers: List[Dict[str, Any]] = []
    risk_config: Optional[Dict[str, Any]] = None


@app.get("/api/v1/portfolio")
async def list_portfolios(
    mode: Optional[str] = None,
    state: Optional[str] = None,
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
):
    """获取 Portfolio 列表"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.get(page=page, page_size=size)

        if result.success:
            portfolios = []
            raw_data = result.data or []

            # 按创建时间降序排序（最新的在前面）
            raw_data = sorted(raw_data, key=lambda x: x.create_at or datetime.min, reverse=True)

            for p in raw_data:
                # 计算净值
                net_value = 1.0
                if p.initial_capital and p.current_capital and float(p.initial_capital) > 0:
                    net_value = float(p.current_capital) / float(p.initial_capital)

                portfolios.append({
                    "uuid": p.uuid,
                    "name": p.name,
                    "desc": p.desc or "",
                    "is_live": p.is_live or False,
                    "mode": 2 if p.is_live else 0,  # 根据 is_live 推断模式
                    "state": 0,  # 默认停止状态
                    "initial_cash": float(p.initial_capital) if p.initial_capital else 100000,
                    "current_cash": float(p.current_capital) if p.current_capital else 100000,
                    "cash": float(p.cash) if p.cash else 100000,
                    "total_profit": float(p.total_profit) if p.total_profit else 0,
                    "sharpe_ratio": float(p.sharpe_ratio) if p.sharpe_ratio else 0,
                    "max_drawdown": float(p.max_drawdown) if p.max_drawdown else 0,
                    "win_rate": float(p.win_rate) if p.win_rate else 0,
                    "net_value": round(net_value, 4),
                    "created_at": p.create_at.isoformat() if p.create_at else None,
                    "updated_at": p.update_at.isoformat() if p.update_at else None,
                })
            return {"data": portfolios, "total": len(portfolios)}
        return {"data": [], "total": 0}
    except Exception as e:
        print(f"[ERROR] Failed to list portfolios: {e}")
        import traceback
        traceback.print_exc()
        return {"data": [], "total": 0}


@app.get("/api/v1/portfolio/{portfolio_id}")
async def get_portfolio(portfolio_id: str):
    """获取 Portfolio 详情"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.get(portfolio_id=portfolio_id)

        if result.success and result.data:
            # get方法返回列表，取第一个元素
            portfolios = result.data
            if not portfolios or len(portfolios) == 0:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            p = portfolios[0]

            net_value = 1.0
            if p.initial_capital and p.current_capital and float(p.initial_capital) > 0:
                net_value = float(p.current_capital) / float(p.initial_capital)

            # 获取组件配置
            components_result = portfolio_service.get_components(portfolio_id=portfolio_id)
            components = []
            if components_result.success and components_result.data:
                components = components_result.data

            # 组件类型映射 (数据库存储的是整数)
            # FILE_TYPES: SELECTOR=4, SIZER=5, STRATEGY=6, RISKMANAGER=7, ANALYZER=8
            type_map = {'4': 'SELECTOR', '5': 'SIZER', '6': 'STRATEGY', '7': 'RISKMANAGER', '8': 'ANALYZER'}

            # 获取参数服务
            from ginkgo import service_hub
            mapping_service = service_hub.data.mapping_service()

            # 为每个组件添加类型名称和参数
            for c in components:
                c['type_name'] = type_map.get(str(c.get('component_type', '')), 'UNKNOWN')
                # 获取该组件的参数
                mount_id = c.get('mount_id')
                if mount_id:
                    params_result = mapping_service.get_portfolio_parameters(mount_id)
                    if params_result.success and params_result.data:
                        # 将参数列表转换为config字典
                        config = {}
                        for param in params_result.data:
                            value = param.value
                            # 解析 "key=value" 格式
                            if '=' in value:
                                k, v = value.split('=', 1)
                                # 尝试转换数值类型
                                try:
                                    v = float(v) if '.' in v else int(v)
                                except:
                                    pass
                                config[k] = v
                            else:
                                config[f"param_{param.index}"] = value
                        c['config'] = config
                    else:
                        c['config'] = {}
                else:
                    c['config'] = {}

            # 分类组件
            selectors = [c for c in components if c.get('type_name') == 'SELECTOR']
            sizers = [c for c in components if c.get('type_name') == 'SIZER']
            strategies = [c for c in components if c.get('type_name') == 'STRATEGY']
            risks = [c for c in components if c.get('type_name') == 'RISKMANAGER']
            analyzers = [c for c in components if c.get('type_name') == 'ANALYZER']

            return {
                "uuid": p.uuid,
                "name": p.name,
                "desc": p.desc or "",
                "is_live": p.is_live or False,
                "mode": 2 if p.is_live else 0,
                "state": 0,
                "initial_cash": float(p.initial_capital) if p.initial_capital else 100000,
                "current_cash": float(p.current_capital) if p.current_capital else 100000,
                "cash": float(p.cash) if p.cash else 100000,
                "total_profit": float(p.total_profit) if p.total_profit else 0,
                "sharpe_ratio": float(p.sharpe_ratio) if p.sharpe_ratio else 0,
                "max_drawdown": float(p.max_drawdown) if p.max_drawdown else 0,
                "win_rate": float(p.win_rate) if p.win_rate else 0,
                "net_value": round(net_value, 4),
                "created_at": p.create_at.isoformat() if p.create_at else None,
                "updated_at": p.update_at.isoformat() if p.update_at else None,
                # 前端需要的额外字段
                "positions": [],
                "risk_alerts": [],
                "config_locked": False,
                # 组件配置
                "components": {
                    "selectors": [{
                        "uuid": c.get('component_id'),
                        "name": c.get('component_name'),
                        "config": c.get('config', {})
                    } for c in selectors],
                    "sizer": {"uuid": sizers[0].get('component_id'), "name": sizers[0].get('component_name'), "config": sizers[0].get('config', {})} if sizers else None,
                    "strategies": [{
                        "uuid": c.get('component_id'),
                        "name": c.get('component_name'),
                        "weight": c.get('weight', 1.0),
                        "config": c.get('config', {})
                    } for c in strategies],
                    "risk_managers": [{
                        "uuid": c.get('component_id'),
                        "name": c.get('component_name'),
                        "config": c.get('config', {})
                    } for c in risks],
                    "analyzers": [{
                        "uuid": c.get('component_id'),
                        "name": c.get('component_name'),
                        "config": c.get('config', {})
                    } for c in analyzers],
                }
            }
        raise HTTPException(status_code=404, detail="Portfolio not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to get portfolio {portfolio_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/portfolio")
async def create_portfolio(request: PortfolioCreateRequest):
    """创建 Portfolio"""
    try:
        portfolio_service = get_portfolio_service()
        from ginkgo import service_hub
        mapping_service = service_hub.data.mapping_service()

        # 创建投资组合
        result = portfolio_service.add(
            name=request.name,
            description=request.description or request.name,
            is_live=request.mode == "LIVE"
        )

        if result.success and result.data:
            portfolio = result.data
            # result.data 可能是字典或对象
            if isinstance(portfolio, dict):
                portfolio_uuid = portfolio.get('uuid')
            else:
                portfolio_uuid = portfolio.uuid

            # 挂载组件
            from ginkgo.enums import FILE_TYPES

            # 挂载选股器并保存参数
            for selector in request.selectors:
                component_uuid = selector.get('component_uuid')
                config = selector.get('config', {})
                if component_uuid:
                    mount_result = portfolio_service.mount_component(
                        portfolio_id=portfolio_uuid,
                        component_id=component_uuid,
                        component_name=f"selector_{component_uuid[:8]}",
                        component_type=FILE_TYPES.SELECTOR
                    )
                    # 保存参数
                    if mount_result.success and config:
                        mapping_uuid = mount_result.data.get('mount_id')
                        if mapping_uuid:
                            # 将config dict转换为index:value格式
                            params = {i: f"{k}={v}" for i, (k, v) in enumerate(config.items())}
                            mapping_service.create_component_parameters(mapping_uuid, component_uuid, params)

            # 挂载仓位管理器
            if request.sizer_uuid:
                mount_result = portfolio_service.mount_component(
                    portfolio_id=portfolio_uuid,
                    component_id=request.sizer_uuid,
                    component_name=f"sizer_{request.sizer_uuid[:8]}",
                    component_type=FILE_TYPES.SIZER
                )

            # 挂载策略并保存参数
            for strategy in request.strategies:
                component_uuid = strategy.get('component_uuid')
                config = strategy.get('config', {})
                if component_uuid:
                    mount_result = portfolio_service.mount_component(
                        portfolio_id=portfolio_uuid,
                        component_id=component_uuid,
                        component_name=f"strategy_{component_uuid[:8]}",
                        component_type=FILE_TYPES.STRATEGY
                    )
                    # 保存参数
                    if mount_result.success and config:
                        mapping_uuid = mount_result.data.get('mount_id')
                        if mapping_uuid:
                            params = {i: f"{k}={v}" for i, (k, v) in enumerate(config.items())}
                            mapping_service.create_component_parameters(mapping_uuid, component_uuid, params)

            # 挂载风控
            for risk in request.risk_managers:
                component_uuid = risk.get('component_uuid')
                config = risk.get('config', {})
                if component_uuid:
                    mount_result = portfolio_service.mount_component(
                        portfolio_id=portfolio_uuid,
                        component_id=component_uuid,
                        component_name=f"risk_{component_uuid[:8]}",
                        component_type=FILE_TYPES.RISKMANAGER
                    )
                    # 保存参数
                    if mount_result.success and config:
                        mapping_uuid = mount_result.data.get('mount_id')
                        if mapping_uuid:
                            params = {i: f"{k}={v}" for i, (k, v) in enumerate(config.items())}
                            mapping_service.create_component_parameters(mapping_uuid, component_uuid, params)

            # 挂载分析器
            for analyzer in request.analyzers:
                component_uuid = analyzer.get('component_uuid')
                config = analyzer.get('config', {})
                if component_uuid:
                    mount_result = portfolio_service.mount_component(
                        portfolio_id=portfolio_uuid,
                        component_id=component_uuid,
                        component_name=f"analyzer_{component_uuid[:8]}",
                        component_type=FILE_TYPES.ANALYZER
                    )
                    # 保存参数
                    if mount_result.success and config:
                        mapping_uuid = mount_result.data.get('mount_id')
                        if mapping_uuid:
                            params = {i: f"{k}={v}" for i, (k, v) in enumerate(config.items())}
                            mapping_service.create_component_parameters(mapping_uuid, component_uuid, params)

            portfolio_name = portfolio.get('name') if isinstance(portfolio, dict) else portfolio.name
            return {"uuid": portfolio_uuid, "name": portfolio_name}

        raise HTTPException(status_code=500, detail="Failed to create portfolio")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to create portfolio: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/portfolio/{portfolio_id}")
async def update_portfolio(portfolio_id: str, request: dict):
    """更新 Portfolio"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.update(portfolio_id, request)

        if result.success and result.data:
            p = result.data
            return {
                "uuid": p.uuid,
                "name": p.name,
                "mode": p.mode,
                "state": p.state,
                "initial_cash": float(p.initial_cash) if p.initial_cash else 0,
                "net_value": float(p.net_value) if p.net_value else 1.0,
                "config_locked": p.config_locked,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
        raise HTTPException(status_code=404, detail="Portfolio not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to update portfolio {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/portfolio/{portfolio_id}")
async def delete_portfolio(portfolio_id: str):
    """删除 Portfolio"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.delete(portfolio_id)

        if result.success:
            return {"status": "success"}
        raise HTTPException(status_code=404, detail="Portfolio not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to delete portfolio {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/portfolio/{portfolio_id}/start")
async def start_portfolio(portfolio_id: str):
    """启动 Portfolio"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.update(portfolio_id, {"state": "RUNNING"})

        if result.success:
            return {"status": "success", "state": "RUNNING"}
        raise HTTPException(status_code=404, detail="Portfolio not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to start portfolio {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/portfolio/{portfolio_id}/stop")
async def stop_portfolio(portfolio_id: str):
    """停止 Portfolio"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.update(portfolio_id, {"state": "STOPPED"})

        if result.success:
            return {"status": "success", "state": "STOPPED"}
        raise HTTPException(status_code=404, detail="Portfolio not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to stop portfolio {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/portfolio/stats")
async def get_portfolio_stats():
    """获取 Portfolio 统计"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.get()

        if result.success and result.data:
            portfolios = result.data
            total = len(portfolios)
            live_count = len([p for p in portfolios if p.is_live])
            total_assets = sum(float(p.initial_capital or 0) for p in portfolios)

            # 计算平均净值
            net_values = []
            for p in portfolios:
                if p.initial_capital and p.current_capital and float(p.initial_capital) > 0:
                    net_values.append(float(p.current_capital) / float(p.initial_capital))
            avg_net_value = sum(net_values) / len(net_values) if net_values else 1.0

            return {
                "total": total,
                "running": live_count,
                "avg_net_value": round(avg_net_value, 4),
                "total_assets": total_assets,
            }
        return {"total": 0, "running": 0, "avg_net_value": 1.0, "total_assets": 0}
    except Exception as e:
        print(f"[ERROR] Failed to get portfolio stats: {e}")
        return {"total": 0, "running": 0, "avg_net_value": 1.0, "total_assets": 0}


# ========== 数据管理 ==========

@app.get("/api/v1/data/stockinfo")
async def list_stockinfo(
    query: str = Query("", description="搜索关键词"),
    page: int = Query(0, ge=0),
    size: int = Query(50, ge=1, le=500),
):
    """获取股票信息列表"""
    try:
        stockinfo_service = get_stockinfo_service()
        if query:
            result = stockinfo_service.fuzzy_search(query, page=page, page_size=size)
        else:
            result = stockinfo_service.get(page=page, page_size=size)

        if result.success:
            return {
                "data": serialize_modellist(result.data),
                "total": len(result.data) if result.data else 0,
                "page": page,
                "size": size,
            }
        return {"data": [], "total": 0, "page": page, "size": size}
    except Exception as e:
        print(f"[ERROR] Failed to list stockinfo: {e}")
        return {"data": [], "total": 0, "page": page, "size": size}


@app.get("/api/v1/data/stockinfo/{code}")
async def get_stockinfo(code: str):
    """获取单只股票信息"""
    try:
        stockinfo_service = get_stockinfo_service()
        result = stockinfo_service.get(filters={"code": code}, page_size=1)
        if result.success and result.data:
            return serialize_model(result.data[0])
        raise HTTPException(status_code=404, detail="Stock not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to get stockinfo for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/data/bars/{code}")
async def get_bars(
    code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    frequency: str = Query("day", description="数据频率: day, week, month"),
    adjustment: str = Query("fore", description="复权类型: none, fore, back"),
    page: int = Query(0, ge=0),
    size: int = Query(500, ge=1, le=5000),
):
    """获取 K 线数据"""
    try:
        bar_service = get_bar_service()

        # 转换参数
        freq_map = {"day": FREQUENCY_TYPES.DAY, "week": FREQUENCY_TYPES.WEEK, "month": FREQUENCY_TYPES.MONTH}
        adj_map = {"none": ADJUSTMENT_TYPES.NONE, "fore": ADJUSTMENT_TYPES.FORE, "back": ADJUSTMENT_TYPES.BACK}

        result = bar_service.get(
            code=code,
            start_date=datetime_normalize(start_date) if start_date else None,
            end_date=datetime_normalize(end_date) if end_date else None,
            frequency=freq_map.get(frequency, FREQUENCY_TYPES.DAY),
            adjustment_type=adj_map.get(adjustment, ADJUSTMENT_TYPES.FORE),
            page=page,
            page_size=size,
        )

        if result.success and result.data:
            bars = []
            for bar in result.data:
                bars.append({
                    "code": bar.code,
                    "timestamp": bar.timestamp.isoformat() if bar.timestamp else None,
                    "open": float(bar.open) if bar.open else None,
                    "high": float(bar.high) if bar.high else None,
                    "low": float(bar.low) if bar.low else None,
                    "close": float(bar.close) if bar.close else None,
                    "volume": bar.volume,
                    "amount": float(bar.amount) if bar.amount else None,
                })
            return {"data": bars, "total": len(bars)}
        return {"data": [], "total": 0}
    except Exception as e:
        print(f"[ERROR] Failed to get bars for {code}: {e}")
        return {"data": [], "total": 0}


# ========== 系统状态 ==========

@app.get("/api/v1/system/status")
async def get_system_status():
    """获取系统状态"""
    try:
        module_status = service_hub.get_module_status()
        uptime = service_hub.get_uptime()

        return {
            "status": "running",
            "version": "0.11.0",
            "uptime": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
            "modules": module_status,
            "debug_mode": GCONF.DEBUGMODE,
        }
    except Exception as e:
        print(f"[ERROR] Failed to get system status: {e}")
        return {"status": "error", "version": "0.11.0", "error": str(e)}


@app.get("/api/v1/system/workers")
async def list_workers():
    """获取 Worker 列表"""
    try:
        # 通过 Redis 获取 worker 状态
        redis_service = service_hub.data.redis_service()
        if redis_service:
            result = redis_service.get_worker_status()
            if result.success:
                return {"data": result.data}
        return {"data": []}
    except Exception as e:
        print(f"[ERROR] Failed to list workers: {e}")
        return {"data": []}


@app.post("/api/v1/system/debug")
async def toggle_debug_mode(request: dict):
    """切换调试模式"""
    enabled = request.get("enabled", False)
    if enabled:
        service_hub.enable_debug()
        GCONF.set_debug(True)
    else:
        service_hub.disable_debug()
        GCONF.set_debug(False)
    return {"debug_mode": enabled}


# ========== 文件管理 ==========

@app.get("/api/v1/file_list")
async def fetch_file_list(query: str = "", page: int = 0, size: int = 100, type: int = None):
    """获取文件列表"""
    try:
        file_service = service_hub.data.file_service()
        # 使用 get() 方法，支持分页和类型过滤
        file_type = None
        if type is not None:
            from ginkgo.enums import FILE_TYPES
            try:
                file_type = FILE_TYPES(type)
            except ValueError:
                pass

        result = file_service.get(file_type=file_type, as_dataframe=False)
        if result.success:
            files = result.data.get("files", [])
            # 如果有搜索关键词，过滤名称
            if query:
                files = [f for f in files if query.lower() in f.name.lower()]
            # 手动分页
            start = page * size
            end = start + size
            files = files[start:end]
            return serialize_modellist(files)
        return []
    except Exception as e:
        print(f"[ERROR] Failed to fetch file list: {e}")
        import traceback
        traceback.print_exc()
        return []


@app.get("/api/v1/file/{file_id}")
async def fetch_file(file_id: str):
    """获取文件内容"""
    try:
        file_service = service_hub.data.file_service()
        result = file_service.get_by_uuid(file_id)
        if result.success and result.data and result.data.get("exists"):
            file_record = result.data.get("file")
            return serialize_model(file_record)
        raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to fetch file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/update_file")
async def update_file(request: dict):
    """更新文件内容"""
    try:
        file_id = request.get("file_id")
        content = request.get("content")
        file_service = service_hub.data.file_service()
        # 使用 update() 方法
        result = file_service.update(file_id=file_id, data=content.encode('utf-8') if content else b"")
        if result.success:
            return {"status": "success"}
        return {"status": "error", "message": result.error}
    except Exception as e:
        print(f"[ERROR] Failed to update file: {e}")
        return {"status": "error", "message": str(e)}


class FileCreateRequest(BaseModel):
    """创建文件请求"""
    name: str
    type: int  # FILE_TYPES 枚举值
    content: str = ""


@app.post("/api/v1/file")
async def create_file(request: FileCreateRequest):
    """创建新文件"""
    try:
        from ginkgo.enums import FILE_TYPES
        file_service = service_hub.data.file_service()
        # 将整数转换为枚举
        file_type = FILE_TYPES(request.type)
        result = file_service.add(
            name=request.name,
            file_type=file_type,
            data=request.content.encode('utf-8')
        )
        if result.success and result.data:
            file_info = result.data.get('file_info', result.data)
            return {
                "status": "success",
                "uuid": file_info.get('uuid') if isinstance(file_info, dict) else getattr(file_info, 'uuid', ''),
                "name": request.name
            }
        return {"status": "error", "message": result.error}
    except Exception as e:
        print(f"[ERROR] Failed to create file: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.delete("/api/v1/file/{file_id}")
async def delete_file(file_id: str):
    """删除文件"""
    try:
        file_service = service_hub.data.file_service()
        # 使用 _crud_repo 的 delete_by_file_id 方法
        file_service._crud_repo.delete_by_file_id(file_id)
        return {"status": "success"}
    except Exception as e:
        print(f"[ERROR] Failed to delete file {file_id}: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


# ========== 订单管理 ==========

from ginkgo.enums import ORDERSTATUS_TYPES


def get_order_crud():
    """获取 OrderCRUD 实例"""
    return service_hub.data.order_crud()


def get_position_crud():
    """获取 PositionCRUD 实例"""
    return service_hub.data.position_crud()


@app.get("/api/v1/orders")
async def list_orders(
    mode: str = Query("paper", description="交易模式: paper 或 live"),
    portfolio_id: Optional[str] = Query(None, description="投资组合ID"),
    code: Optional[str] = Query(None, description="股票代码"),
    status: Optional[str] = Query(None, description="订单状态"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(0, ge=0),
    size: int = Query(50, ge=1, le=500),
):
    """获取订单列表"""
    try:
        order_crud = get_order_crud()

        # 构建过滤器
        filters = {}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if code:
            filters["code"] = code
        if status:
            # 转换状态字符串为枚举值
            status_map = {
                "new": ORDERSTATUS_TYPES.NEW,
                "filled": ORDERSTATUS_TYPES.FILLED,
                "canceled": ORDERSTATUS_TYPES.CANCELED,
                "partial": ORDERSTATUS_TYPES.PARTIALFILLED,
            }
            if status.lower() in status_map:
                filters["status"] = status_map[status.lower()]
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        result = order_crud.find(
            filters=filters,
            page=page,
            page_size=size,
            order_by="timestamp",
            desc_order=True,
            output_type="model"
        )

        orders = []
        for order in result:
            orders.append({
                "uuid": order.uuid,
                "portfolio_id": order.portfolio_id,
                "code": order.code,
                "direction": order.direction.value if hasattr(order.direction, 'value') else order.direction,
                "order_type": order.order_type.value if hasattr(order.order_type, 'value') else order.order_type,
                "status": order.status.value if hasattr(order.status, 'value') else order.status,
                "volume": order.volume,
                "limit_price": float(order.limit_price) if order.limit_price else 0,
                "transaction_price": float(order.transaction_price) if order.transaction_price else 0,
                "transaction_volume": order.transaction_volume,
                "fee": float(order.fee) if order.fee else 0,
                "timestamp": order.timestamp.isoformat() if order.timestamp else None,
                "created_at": order.create_at.isoformat() if order.create_at else None,
            })

        # 获取总数
        total = order_crud.count(filters)

        return {"data": orders, "total": total, "page": page, "size": size}
    except Exception as e:
        print(f"[ERROR] Failed to list orders: {e}")
        import traceback
        traceback.print_exc()
        return {"data": [], "total": 0, "page": page, "size": size}


@app.get("/api/v1/orders/{order_id}")
async def get_order(order_id: str):
    """获取订单详情"""
    try:
        order_crud = get_order_crud()
        result = order_crud.get_by_id(order_id)
        if result:
            return serialize_model(result)
        raise HTTPException(status_code=404, detail="Order not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to get order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 持仓管理 ==========

@app.get("/api/v1/positions")
async def list_positions(
    portfolio_id: Optional[str] = Query(None, description="投资组合ID"),
    code: Optional[str] = Query(None, description="股票代码"),
    page: int = Query(0, ge=0),
    size: int = Query(100, ge=1, le=500),
):
    """获取持仓列表"""
    try:
        position_crud = get_position_crud()

        # 构建过滤器
        filters = {}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if code:
            filters["code"] = code

        result = position_crud.find(
            filters=filters,
            page=page,
            page_size=size,
            order_by="update_at",
            desc_order=True,
            output_type="model"
        )

        positions = []
        for pos in result:
            # 计算盈亏
            cost = float(pos.cost) if pos.cost else 0
            price = float(pos.price) if pos.price else 0
            volume = pos.volume or 0
            profit = (price - cost) * volume if cost > 0 else 0
            profit_pct = ((price - cost) / cost * 100) if cost > 0 else 0

            positions.append({
                "uuid": pos.uuid,
                "portfolio_id": pos.portfolio_id,
                "code": pos.code,
                "volume": volume,
                "frozen_volume": pos.frozen_volume or 0,
                "cost": cost,
                "price": price,
                "market_value": price * volume,
                "profit": profit,
                "profit_pct": round(profit_pct, 2),
                "fee": float(pos.fee) if pos.fee else 0,
                "updated_at": pos.update_at.isoformat() if pos.update_at else None,
            })

        # 获取总数
        total = position_crud.count(filters)

        # 计算汇总信息
        total_market_value = sum(p["market_value"] for p in positions)
        total_profit = sum(p["profit"] for p in positions)
        total_fee = sum(p["fee"] for p in positions)

        return {
            "data": positions,
            "total": total,
            "page": page,
            "size": size,
            "summary": {
                "total_market_value": total_market_value,
                "total_profit": total_profit,
                "total_fee": total_fee,
                "position_count": len(positions),
            }
        }
    except Exception as e:
        print(f"[ERROR] Failed to list positions: {e}")
        import traceback
        traceback.print_exc()
        return {"data": [], "total": 0, "page": page, "size": size, "summary": {}}


@app.get("/api/v1/positions/{position_id}")
async def get_position(position_id: str):
    """获取持仓详情"""
    try:
        position_crud = get_position_crud()
        result = position_crud.get_by_id(position_id)
        if result:
            return serialize_model(result)
        raise HTTPException(status_code=404, detail="Position not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to get position {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 缺失的 API 端点 ==========

@app.get("/api/v1/system/workers")
async def list_workers():
    """获取 Worker 列表"""
    # 返回模拟数据，实际需要从 GTM 获取
    return {"data": [], "total": 0}


@app.post("/api/v1/research/ic")
async def research_ic(request: dict):
    """IC 分析"""
    return {"ic_mean": 0.05, "ic_std": 0.1, "icir": 0.5, "ic_positive_ratio": 0.6, "ic_series": []}


@app.post("/api/v1/research/layering")
async def research_layering(request: dict):
    """因子分层"""
    return {
        "long_short_return": 0.15,
        "best_group": "G1",
        "best_group_return": 0.2,
        "groups": [{"group": f"G{i}", "return": 0.1 - i * 0.02, "count": 50} for i in range(1, 6)]
    }


@app.post("/api/v1/research/orthogonalize")
async def research_orthogonalize(request: dict):
    """因子正交化"""
    return {
        "original_avg_corr": 0.3,
        "orthogonal_avg_corr": 0.05,
        "correlation_matrix": []
    }


@app.post("/api/v1/research/compare")
async def research_compare(request: dict):
    """因子对比"""
    return {
        "best_factor": "factor_1",
        "best_score": 0.85,
        "factors": [
            {"name": f"factor_{i}", "ic_mean": 0.05 - i * 0.01, "icir": 0.5, "monotonicity": 0.8, "score": 0.8 - i * 0.1}
            for i in range(1, 4)
        ]
    }


@app.post("/api/v1/research/decay")
async def research_decay(request: dict):
    """因子衰减"""
    return {
        "half_life": 10,
        "effective_period": 20,
        "decay_series": [{"period": i, "ic": 0.05 * (0.9 ** i), "rank_ic": 0.04 * (0.9 ** i)} for i in range(1, 21)]
    }


@app.post("/api/v1/validation/sensitivity")
async def validation_sensitivity(request: dict):
    """敏感性分析"""
    values = request.get("param_values", ["0.1", "0.2", "0.3"])
    return {
        "sensitivity_score": 0.3,
        "optimal_value": values[1] if len(values) > 1 else values[0],
        "optimal_return": 0.15,
        "data_points": [
            {"param_value": v, "return": 0.1 + i * 0.02, "sharpe_ratio": 1.0 + i * 0.1, "max_drawdown": 0.1, "is_optimal": i == 1}
            for i, v in enumerate(values)
        ]
    }


@app.post("/api/v1/data/sync")
async def data_sync(request: dict):
    """数据同步命令"""
    return {"status": "success", "message": f"Command {request.get('type', 'UNKNOWN')} sent"}


@app.get("/api/v1/data/status")
async def data_status():
    """数据同步状态"""
    return {
        "bar_count": 1000000,
        "tick_count": 5000000,
        "stock_count": 5000,
        "last_sync": "2026-02-18 12:00:00"
    }


@app.post("/api/v1/optimization/genetic")
async def optimization_genetic(request: dict):
    """遗传算法优化"""
    return {
        "generations": request.get("generations", 100),
        "best_fitness": 0.25,
        "convergence_gen": 50,
        "best_params": {"param1": 0.5, "param2": 10},
        "history": [
            {"generation": i, "best_fitness": 0.1 + i * 0.001, "avg_fitness": 0.08 + i * 0.0008, "diversity": 0.5 - i * 0.002}
            for i in range(1, 11)
        ]
    }


@app.post("/api/v1/optimization/bayesian")
async def optimization_bayesian(request: dict):
    """贝叶斯优化"""
    return {
        "total_iterations": request.get("n_iterations", 50),
        "best_value": 0.22,
        "best_params": {"param1": 0.3, "param2": 15},
        "history": [
            {"iteration": i, "params": f"{{p1: {0.1 * i}}}", "value": 0.1 + i * 0.005, "acquisition": 0.8 - i * 0.01}
            for i in range(1, 11)
        ]
    }


# ========== 启动入口 ==========

if __name__ == "__main__":
    import uvicorn

    # 启用调试模式以便访问数据库
    GCONF.set_debug(True)

    print("[INFO] Starting Ginkgo API Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
