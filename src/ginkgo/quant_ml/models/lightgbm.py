"""
LightGBM模型实现

基于qlib的LGBModel设计，适配ginkgo的IModel接口。
支持回归和分类任务，包含早停、特征重要性分析等功能。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    lgb = None

from ginkgo.core.interfaces.model_interface import IModel, ModelStatus
from ginkgo.enums import MODEL_TYPES
from ginkgo.libs import GLOG


class LightGBMModel(IModel):
    """
    LightGBM模型实现
    
    参考qlib的LGBModel设计，支持：
    - 回归和分类任务
    - 早停机制
    - 特征重要性分析
    - 交叉验证
    - 模型微调
    """
    
    DEFAULT_PARAMS = {
        "objective": "regression",
        "metric": "rmse",
        "verbosity": -1,
        "seed": 42,
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "min_child_samples": 20,
    }
    
    def __init__(self, 
                 name: str = "LightGBM",
                 task: str = "regression",
                 early_stopping_rounds: int = 50,
                 num_boost_round: int = 1000,
                 **kwargs):
        """
        初始化LightGBM模型
        
        Args:
            name: 模型名称
            task: 任务类型 ("regression" 或 "classification")
            early_stopping_rounds: 早停轮数
            num_boost_round: 最大训练轮数
            **kwargs: 其他LightGBM参数
        """
        if not LIGHTGBM_AVAILABLE:
            raise ImportError("LightGBM未安装，请运行: pip install lightgbm")
        
        super().__init__(name, MODEL_TYPES.TABULAR)
        
        # 任务配置
        self.task = task
        self.early_stopping_rounds = early_stopping_rounds
        self.num_boost_round = num_boost_round
        
        # 合并默认参数和用户参数
        self._hyperparameters = self.DEFAULT_PARAMS.copy()
        if task == "classification":
            self._hyperparameters["objective"] = "binary"
            self._hyperparameters["metric"] = "binary_logloss"
        
        self._hyperparameters.update(kwargs)
        
        # 模型对象
        self.model = None
        self._training_datasets = []
        self._evals_result = {}
        
        GLOG.INFO(f"初始化LightGBM模型: {name}, 任务类型: {task}")
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'LightGBMModel':
        """
        训练LightGBM模型
        
        Args:
            X: 特征数据
            y: 目标变量
            **kwargs: 训练参数
                - eval_set: 验证集 [(X_val, y_val), ...]
                - verbose_eval: 打印间隔
                - reweight: 样本权重
        """
        if y is None:
            raise ValueError("LightGBM需要目标变量y进行监督学习")
        
        try:
            self.update_status(ModelStatus.TRAINING)
            
            # 记录特征和目标信息
            self._feature_names = list(X.columns)
            self._target_names = list(y.columns) if hasattr(y, 'columns') else ['target']
            
            # 处理目标变量格式（LightGBM需要1D数组）
            y_array = self._prepare_target(y)
            
            # 创建训练数据集
            sample_weight = kwargs.get('reweight', None)
            train_data = lgb.Dataset(
                X.values, 
                label=y_array,
                weight=sample_weight,
                feature_name=self._feature_names
            )
            
            # 准备验证数据集
            valid_sets = [train_data]
            valid_names = ['train']
            
            eval_set = kwargs.get('eval_set', [])
            for i, (X_val, y_val) in enumerate(eval_set):
                y_val_array = self._prepare_target(y_val)
                valid_data = lgb.Dataset(
                    X_val.values,
                    label=y_val_array,
                    reference=train_data,
                    feature_name=self._feature_names
                )
                valid_sets.append(valid_data)
                valid_names.append(f'valid_{i}')
            
            # 训练参数
            num_boost_round = kwargs.get('num_boost_round', self.num_boost_round)
            early_stopping_rounds = kwargs.get('early_stopping_rounds', self.early_stopping_rounds)
            verbose_eval = kwargs.get('verbose_eval', 20)
            
            # 重置结果记录
            self._evals_result = {}
            
            # 设置回调函数
            callbacks = []
            if early_stopping_rounds and len(valid_sets) > 1:
                callbacks.append(lgb.early_stopping(early_stopping_rounds))
            if verbose_eval:
                callbacks.append(lgb.log_evaluation(period=verbose_eval))
            callbacks.append(lgb.record_evaluation(self._evals_result))
            
            # 训练模型
            GLOG.INFO(f"开始训练LightGBM模型，特征数: {X.shape[1]}, 样本数: {X.shape[0]}")
            
            self.model = lgb.train(
                self._hyperparameters,
                train_data,
                num_boost_round=num_boost_round,
                valid_sets=valid_sets,
                valid_names=valid_names,
                callbacks=callbacks
            )
            
            # 记录训练历史
            self._record_training_history()
            
            # 更新状态
            self.update_status(ModelStatus.TRAINED)
            
            GLOG.INFO(f"LightGBM训练完成，最终轮数: {self.model.current_iteration()}")
            return self
            
        except Exception as e:
            self.update_status(ModelStatus.UNTRAINED)
            GLOG.ERROR(f"LightGBM训练失败: {e}")
            raise e
    
    def predict(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        使用训练好的模型进行预测
        
        Args:
            X: 特征数据
            **kwargs: 预测参数
                - num_iteration: 使用的迭代轮数
        """
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，请先调用fit方法")
        
        try:
            num_iteration = kwargs.get('num_iteration', None)
            predictions = self.model.predict(
                X.values,
                num_iteration=num_iteration
            )
            
            # 转换为DataFrame格式
            if self.task == "classification" and predictions.ndim > 1:
                # 多分类情况
                columns = [f'prob_class_{i}' for i in range(predictions.shape[1])]
                return pd.DataFrame(predictions, index=X.index, columns=columns)
            else:
                # 回归或二分类
                return pd.DataFrame(
                    predictions,
                    index=X.index,
                    columns=['prediction']
                )
                
        except Exception as e:
            GLOG.ERROR(f"LightGBM预测失败: {e}")
            raise e
    
    def predict_proba(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """预测类别概率（仅用于分类任务）"""
        if self.task != "classification":
            raise NotImplementedError("概率预测仅适用于分类任务")
        
        return self.predict(X, **kwargs)
    
    def get_feature_importance(self) -> Optional[pd.Series]:
        """获取特征重要性"""
        if not self.is_trained:
            return None
        
        importance = self.model.feature_importance(importance_type='gain')
        return pd.Series(
            importance,
            index=self._feature_names,
            name='importance'
        ).sort_values(ascending=False)
    
    def set_hyperparameters(self, **hyperparams) -> None:
        """设置超参数"""
        self._hyperparameters.update(hyperparams)
        GLOG.INFO(f"更新超参数: {hyperparams}")
    
    def validate_hyperparameters(self) -> bool:
        """验证超参数有效性"""
        required_params = ['objective', 'metric']
        for param in required_params:
            if param not in self._hyperparameters:
                GLOG.WARN(f"缺少必需参数: {param}")
                return False
        return True
    
    def finetune(self, X: pd.DataFrame, y: pd.DataFrame, 
                 num_boost_round: int = 10, **kwargs) -> 'LightGBMModel':
        """
        模型微调
        
        Args:
            X: 新的特征数据
            y: 新的目标变量
            num_boost_round: 微调轮数
            **kwargs: 其他参数
        """
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，无法进行微调")
        
        try:
            GLOG.INFO(f"开始LightGBM模型微调，轮数: {num_boost_round}")
            
            # 准备数据
            y_array = self._prepare_target(y)
            train_data = lgb.Dataset(
                X.values,
                label=y_array,
                feature_name=self._feature_names
            )
            
            # 微调参数
            finetune_params = self._hyperparameters.copy()
            finetune_params.update(kwargs)
            
            # 继续训练
            self.model = lgb.train(
                finetune_params,
                train_data,
                num_boost_round=num_boost_round,
                init_model=self.model,
                valid_sets=[train_data],
                valid_names=['finetune']
            )
            
            GLOG.INFO("LightGBM模型微调完成")
            return self
            
        except Exception as e:
            GLOG.ERROR(f"LightGBM微调失败: {e}")
            raise e
    
    def _prepare_target(self, y: Union[pd.DataFrame, pd.Series, np.ndarray]) -> np.ndarray:
        """准备目标变量格式"""
        if isinstance(y, pd.DataFrame):
            if y.shape[1] == 1:
                return y.values.ravel()
            else:
                raise ValueError("LightGBM不支持多标签训练")
        elif isinstance(y, pd.Series):
            return y.values
        elif isinstance(y, np.ndarray):
            if y.ndim == 2 and y.shape[1] == 1:
                return y.ravel()
            elif y.ndim == 1:
                return y
            else:
                raise ValueError("目标变量维度不正确")
        else:
            return np.array(y)
    
    def _record_training_history(self) -> None:
        """记录训练历史"""
        if not self._evals_result:
            return
        
        # 提取训练指标
        for dataset_name, metrics in self._evals_result.items():
            for metric_name, values in metrics.items():
                for epoch, value in enumerate(values):
                    self.add_training_record(
                        {f"{dataset_name}_{metric_name}": value},
                        epoch
                    )
        
        # 设置最终验证指标
        if 'valid_0' in self._evals_result:
            final_metrics = {}
            for metric_name, values in self._evals_result['valid_0'].items():
                if values:
                    final_metrics[f"final_{metric_name}"] = values[-1]
            self.set_validation_metrics(final_metrics)
    
    def get_training_info(self) -> Dict[str, Any]:
        """获取训练信息"""
        if not self.is_trained:
            return {}
        
        return {
            "num_iterations": self.model.current_iteration(),
            "num_features": self.model.num_feature(),
            "objective": self.model.params.get("objective", "unknown"),
            "best_iteration": getattr(self.model, "best_iteration", -1),
            "feature_names": self._feature_names,
            "feature_importances": self.get_feature_importance().to_dict() if self.get_feature_importance() is not None else {}
        }
    
    def save(self, filepath: str, **kwargs) -> None:
        """保存模型"""
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，无法保存")
        
        # 保存LightGBM模型
        model_path = filepath.replace('.pkl', '.lgb')
        self.model.save_model(model_path)
        
        # 保存元数据
        super().save(filepath, **kwargs)
        
        GLOG.INFO(f"LightGBM模型已保存: {filepath}")
    
    @classmethod
    def load(cls, filepath: str, **kwargs) -> 'LightGBMModel':
        """加载模型"""
        # 先加载元数据
        base_model = super().load(filepath, **kwargs)
        
        # 加载LightGBM模型
        model_path = filepath.replace('.pkl', '.lgb')
        if model_path != filepath:
            base_model.model = lgb.Booster(model_file=model_path)
        
        GLOG.INFO(f"LightGBM模型已加载: {filepath}")
        return base_model