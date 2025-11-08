"""
Example Data Seeding

This module is responsible for initializing the database with a set of
example data for backtesting and demonstration purposes.

Updated to use the new DI container architecture with service layer.
"""

import os
import time
import json
from typing import Dict, Any, Optional
from rich.console import Console

# Import the container instance to access services
from ginkgo.data.containers import container

from ginkgo.libs import GCONF, GLOG
from ginkgo.enums import FILE_TYPES
from ginkgo.data.models import MEngine, MPortfolio

console = Console()


def _init_example_engine() -> Dict[str, Any]:
    """Initialize example backtest engine using engine service."""
    engine_service = container.engine_service()
    engine_name = "preset_backtest_engine"

    # 1. Force delete existing engines using hard delete
    existing_engines = engine_service.get_engines(name=engine_name, as_dataframe=True)
    if not existing_engines.empty:
        engine_ids = existing_engines["uuid"].tolist()
        deleted_count = 0
        try:
            with engine_service.crud_repo.get_session() as session:
                for engine_id in engine_ids:
                    engine_service.crud_repo.delete_by_uuid(engine_id, session=session)
                    deleted_count += 1
            console.print(f":broom: Hard deleted {deleted_count} existing '{engine_name}' engines.")
        except Exception as e:
            console.print(f":warning: Engine hard deletion had issues: {str(e)}")

    # 2. Verify deletion completed
    remaining = engine_service.get_engines(name=engine_name, as_dataframe=True)
    if remaining.empty:
        console.print(f":white_check_mark: Verified engine deletion completed.")
    else:
        console.print(f":warning: Still {len(remaining)} engines remaining, but continuing creation.")
        time.sleep(2)

    # 3. Create new engine
    engine = engine_service.create_engine(name=engine_name, is_live=False)
    console.print(f":gear: Example engine '{engine_name}' created.")
    return engine


def _init_example_files() -> int:
    """Initialize example files using file service."""
    file_service = container.file_service()
    file_root = os.path.join(GCONF.WORKING_PATH, "src", "ginkgo", "backtest")
    file_type_map = {
        "analysis/analyzers": FILE_TYPES.ANALYZER,
        "strategy/risk_managementss": FILE_TYPES.RISKMANAGER,
        "strategy/selectors": FILE_TYPES.SELECTOR,
        "strategy/sizers": FILE_TYPES.SIZER,
        "strategy/strategies": FILE_TYPES.STRATEGY,
    }

    files_created = 0
    blacklist = ["__", "base"]

    for folder, file_type in file_type_map.items():
        folder_path = os.path.join(file_root, folder)
        if not os.path.isdir(folder_path):
            console.print(f":warning: Folder not found: {folder_path}")
            continue

        for file_name in os.listdir(folder_path):
            if any(substring in file_name for substring in blacklist) or not file_name.endswith(".py"):
                continue

            preset_name = f"preset_{file_name.split('.')[0]}"

            # Remove existing files with same name and type using hard delete
            existing_files = file_service.get_files(name=preset_name, file_type=file_type, as_dataframe=True)
            if not existing_files.empty:
                file_ids = existing_files["uuid"].tolist()
                deleted_count = 0
                try:
                    with file_service.crud_repo.get_session() as session:
                        for file_id in file_ids:
                            file_service.crud_repo.remove(filters={"uuid": file_id}, session=session)
                            deleted_count += 1
                    console.print(f":broom: Hard deleted {deleted_count} existing '{preset_name}' files.")
                except Exception as e:
                    console.print(f":warning: File hard deletion had issues: {str(e)}")

            # Read and add new file
            file_path = os.path.join(folder_path, file_name)
            with open(file_path, "rb") as f:
                content = f.read()

            result = file_service.add_file(name=preset_name, file_type=file_type, data=content)
            if result.get("success", False):
                files_created += 1
                console.print(f":white_check_mark: Created {file_type.name}: {preset_name}")
            else:
                console.print(f":x: Failed to create {preset_name}: {result.get('error', 'Unknown error')}")

    console.print(f":file_folder: {files_created} example files initialized from {file_root}")
    return files_created


def _init_example_portfolio() -> Dict[str, Any]:
    """Initialize example portfolio using portfolio service."""
    portfolio_service = container.portfolio_service()
    portfolio_name = "preset_portfolio_demo"

    # 1. Force delete existing portfolios using hard delete
    existing_portfolios = portfolio_service.get_portfolios(name=portfolio_name, as_dataframe=True)
    if not existing_portfolios.empty:
        portfolio_ids = existing_portfolios["uuid"].tolist()
        deleted_count = 0
        try:
            with portfolio_service.crud_repo.get_session() as session:
                for portfolio_id in portfolio_ids:
                    portfolio_service.crud_repo.remove(filters={"uuid": portfolio_id}, session=session)
                    deleted_count += 1
            console.print(f":broom: Hard deleted {deleted_count} existing '{portfolio_name}' portfolios.")
        except Exception as e:
            console.print(f":warning: Portfolio hard deletion had issues: {str(e)}")

    # 2. Verify deletion completed
    remaining = portfolio_service.get_portfolios(name=portfolio_name, as_dataframe=True)
    if remaining.empty:
        console.print(f":white_check_mark: Verified portfolio deletion completed.")
    else:
        console.print(f":warning: Still {len(remaining)} portfolios remaining, but continuing creation.")

    # 3. Create new portfolio
    portfolio = portfolio_service.create_portfolio(
        name=portfolio_name, backtest_start_date="2020-01-01", backtest_end_date="2021-01-01", is_live=False
    )
    console.print(f":briefcase: Example portfolio '{portfolio_name}' created.")
    return portfolio


def _validate_sample_data() -> bool:
    """Validate that sample data exists for backtesting."""
    try:
        stockinfo_service = container.stockinfo_service()
        stocks = stockinfo_service.get_stockinfos(page_size=5, as_dataframe=True)

        if stocks.empty:
            console.print(
                ":warning: No stock information found. Run 'ginkgo data update --stockinfo' to populate sample data."
            )
            return False

        console.print(f":white_check_mark: Found {len(stocks)} sample stocks")
        return True
    except Exception as e:
        console.print(f":x: Failed to validate sample data: {e}")
        return False


def run():
    """Runs the entire example data seeding process with enhanced component mapping."""
    console.print("--- Initializing Example Data ---")

    # Check if sample data exists
    if not _validate_sample_data():
        console.print(":information: Consider running 'ginkgo data update --stockinfo' to get sample data")

    # Initialize core components
    engine = _init_example_engine()
    files_created = _init_example_files()
    portfolio = _init_example_portfolio()

    if files_created == 0:
        console.print(":warning: No files were created, cannot proceed with component mapping")
        return

    # Create engine-portfolio mapping
    engine_service = container.engine_service()

    # Extract UUIDs from service results
    engine_id = engine.get("engine_info", {}).get("uuid") if engine.get("success") else None
    portfolio_id = portfolio.get("portfolio_info", {}).get("uuid") if portfolio.get("success") else None

    if not engine_id:
        console.print(f":x: Failed to get engine UUID from result: {engine}")
        return
    if not portfolio_id:
        console.print(f":x: Failed to get portfolio UUID from result: {portfolio}")
        return

    engine_mapping = engine_service.add_portfolio_to_engine(engine_id=engine_id, portfolio_id=portfolio_id)
    console.print(f":link: Engine-portfolio mapping created")

    # Initialize services
    file_service = container.file_service()
    portfolio_service = container.portfolio_service()

    # Define component mapping with parameters
    component_configs = [
        {
            "file_type": FILE_TYPES.STRATEGY,
            "file_name": "preset_random_choice",
            "mapping_name": "example_strategy_random_choice",
            "params": [(0, "ExampleRandomChoice")],
        },
        {
            "file_type": FILE_TYPES.STRATEGY,
            "file_name": "preset_loss_limit",
            "mapping_name": "example_strategy_loss_limit",
            "params": [(0, "ExampleLossLimit"), (1, "13.5")],
        },
        {
            "file_type": FILE_TYPES.SELECTOR,
            "file_name": "preset_fixed_selector",
            "mapping_name": "example_fixed_selector",
            "params": [(0, "example_fixed_selector"), (1, json.dumps(["600594.SH", "600000.SH"]))],
        },
        {
            "file_type": FILE_TYPES.SIZER,
            "file_name": "preset_fixed_sizer",
            "mapping_name": "example_fixed_sizer",
            "params": [(0, "example_fixed_sizer"), (1, "500")],
        },
        {
            "file_type": FILE_TYPES.ANALYZER,
            "file_name": "preset_profit",
            "mapping_name": "example_profit",
            "params": [(0, "example_profit")],
        },
        {
            "file_type": FILE_TYPES.RISKMANAGER,
            "file_name": "preset_no_risk",
            "mapping_name": "example_no_risk",
            "params": [(0, "example_no_risk")],
        },
    ]

    # Map components with parameters
    for config in component_configs:
        try:
            # Get file by name and type
            files = file_service.get_files(name=config["file_name"], file_type=config["file_type"], as_dataframe=True)

            if files.empty:
                console.print(f":warning: Component not found: {config['file_name']}")
                continue

            component_file = files.iloc[0]

            # Create portfolio-file mapping
            mapping = portfolio_service.add_file_to_portfolio(
                portfolio_id=portfolio_id,
                file_id=component_file["uuid"],
                name=config["mapping_name"],
                file_type=config["file_type"],
            )

            # Extract mapping UUID from service result
            mapping_uuid = mapping.get("mapping_info", {}).get("uuid") if mapping.get("success") else None
            if not mapping_uuid:
                console.print(f":x: Failed to get mapping UUID for {config['file_name']}")
                continue

            # Add parameters
            for param_order, param_value in config["params"]:
                portfolio_service.add_parameter(mapping_id=mapping_uuid, index=param_order, value=param_value)

            console.print(
                f":white_check_mark: Mapped {config['file_type'].name}: {config['file_name']} with {len(config['params'])} parameters"
            )

        except Exception as e:
            console.print(f":x: Failed to map {config['file_name']}: {e}")
            GLOG.ERROR(f"Component mapping failed: {e}")

    console.print(":link: Complete mappings for engine, portfolio, and all components created.")
    console.print(":sunglasses: Example data includes parameterized strategies, selectors, sizers, and analyzers.")
    console.print("--- Example Data Initialization Complete ---")
