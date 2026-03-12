# 临时文件：start 函数的正确实现

@app.post("/api/v1/backtest/{backtest_id}/start")
async def start_backtest(backtest_id: str):
    """
    启动回测任务（操作）

    从任务记录中读取配置并启动，不接受参数。
    如需修改配置，请使用编辑接口。
    """
    task_service = get_backtest_task_service()

    # 获取任务记录
    task_result = task_service.get_by_id(backtest_id)
    if not task_result.is_success() or not task_result.data:
        raise HTTPException(status_code=404, detail="Backtest task not found")

    task = task_result.data

    # 从任务记录中获取 portfolio_id
    if not task.portfolio_id:
        raise HTTPException(
            status_code=400,
            detail="Task has no portfolio_id. Please recreate the task with a valid portfolio."
        )

    # 从配置快照中获取参数
    import json
    config_snapshot = {}
    try:
        if task.config_snapshot:
            config_snapshot = json.loads(task.config_snapshot)
    except:
        pass

    # 获取日期参数
    start_date = config_snapshot.get("start_date", "")
    end_date = config_snapshot.get("end_date", "")
    if not start_date and task.backtest_start_date:
        start_date = task.backtest_start_date.strftime("%Y-%m-%d")
    if not end_date and task.backtest_end_date:
        end_date = task.backtest_end_date.strftime("%Y-%m-%d")

    # 其他参数
    initial_cash = config_snapshot.get("initial_cash", 100000.0)
    analyzers = config_snapshot.get("analyzers", [])
    task_name = task.name or f"backtest_{task.run_id[:8]}"

    # 启动任务
    result = task_service.start_task(
        uuid=backtest_id,
        portfolio_uuid=task.portfolio_id,
        name=task_name,
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash,
        analyzers=analyzers,
    )

    if result.is_success():
        return {"success": True, "run_id": result.data.get("run_id"), "message": result.message}
    raise HTTPException(status_code=404 if "not found" in result.error.lower() else 500, detail=result.error)
