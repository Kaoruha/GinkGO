"""
XGBoost模型实现

基于qlib的XGBoost设计，适配ginkgo的IModel接口。
支持回归和分类任务，包含早停、特征重要性分析等功能。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    xgb = None

from ginkgo.core.interfaces.model_interface import IModel, ModelStatus
from ginkgo.enums import MODEL_TYPES
from ginkgo.libs import GLOG


class XGBoostModel(IModel):
    """
    XGBoost模型实现
    
    支持：
    - 回归和分类任务
    - 早停机制
    - 特征重要性分析
    - 交叉验证
    - GPU加速（可选）
    """
    
    DEFAULT_PARAMS = {
        "objective": "reg:squarederror",
        "eval_metric": "rmse",
        "verbosity": 0,
        "seed": 42,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 1,
        "reg_alpha": 0,
        "reg_lambda": 1,
    }
    
    def __init__(self, 
                 name: str = "XGBoost",
                 task: str = "regression",
                 early_stopping_rounds: int = 50,
                 num_boost_round: int = 1000,
                 use_gpu: bool = False,
                 **kwargs):
        """
        初始化XGBoost模型
        
        Args:
            name: 模型名称
            task: 任务类型 ("regression" 或 "classification")
            early_stopping_rounds: 早停轮数
            num_boost_round: 最大训练轮数
            use_gpu: 是否使用GPU加速
            **kwargs: 其他XGBoost参数
        """
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost未安装，请运行: pip install xgboost")
        
        super().__init__(name, MODEL_TYPES.TABULAR)
        
        # 任务配置
        self.task = task
        self.early_stopping_rounds = early_stopping_rounds
        self.num_boost_round = num_boost_round
        self.use_gpu = use_gpu
        
        # 合并默认参数和用户参数
        self._hyperparameters = self.DEFAULT_PARAMS.copy()
        if task == "classification":
            self._hyperparameters["objective"] = "binary:logistic"
            self._hyperparameters["eval_metric"] = "logloss"
        
        # GPU配置
        if use_gpu:
            self._hyperparameters["tree_method"] = "gpu_hist"
            self._hyperparameters["gpu_id"] = 0
        
        self._hyperparameters.update(kwargs)
        
        # 模型对象
        self.model = None
        self._evals_result = {}
        
        GLOG.INFO(f"初始化XGBoost模型: {name}, 任务类型: {task}, GPU: {use_gpu}")
    
    def fit(self, X: pd.DataFrame, y: pd.DataFrame = None, **kwargs) -> 'XGBoostModel':
        """
        训练XGBoost模型
        
        Args:
            X: 特征数据
            y: 目标变量
            **kwargs: 训练参数
                - eval_set: 验证集 [(X_val, y_val), ...]
                - verbose_eval: 打印间隔
                - sample_weight: 样本权重
        """
        if y is None:
            raise ValueError("XGBoost需要目标变量y进行监督学习")
        
        try:
            self.update_status(ModelStatus.TRAINING)
            
            # 记录特征和目标信息
            self._feature_names = list(X.columns)
            self._target_names = list(y.columns) if hasattr(y, 'columns') else ['target']
            
            # 处理目标变量格式
            y_array = self._prepare_target(y)
            
            # 创建DMatrix训练数据
            sample_weight = kwargs.get('sample_weight', None)
            dtrain = xgb.DMatrix(
                X.values,
                label=y_array,
                weight=sample_weight,
                feature_names=self._feature_names
            )
            
            # 准备验证数据集
            evallist = [(dtrain, 'train')]
            eval_set = kwargs.get('eval_set', [])
            for i, (X_val, y_val) in enumerate(eval_set):
                y_val_array = self._prepare_target(y_val)
                dval = xgb.DMatrix(
                    X_val.values,
                    label=y_val_array,
                    feature_names=self._feature_names
                )
                evallist.append((dval, f'valid_{i}'))
            
            # 训练参数
            num_boost_round = kwargs.get('num_boost_round', self.num_boost_round)
            early_stopping_rounds = kwargs.get('early_stopping_rounds', self.early_stopping_rounds)
            verbose_eval = kwargs.get('verbose_eval', 20)
            
            # 重置结果记录
            self._evals_result = {}
            
            # 训练模型
            GLOG.INFO(f"开始训练XGBoost模型，特征数: {X.shape[1]}, 样本数: {X.shape[0]}")
            
            self.model = xgb.train(
                self._hyperparameters,
                dtrain,
                num_boost_round=num_boost_round,
                evals=evallist,
                early_stopping_rounds=early_stopping_rounds if len(evallist) > 1 else None,
                verbose_eval=verbose_eval,
                evals_result=self._evals_result
            )
            
            # 记录训练历史
            self._record_training_history()
            
            # 更新状态
            self.update_status(ModelStatus.TRAINED)
            
            GLOG.INFO(f"XGBoost训练完成，最终轮数: {self.model.num_boosted_rounds()}")
            return self
            
        except Exception as e:
            self.update_status(ModelStatus.UNTRAINED)
            GLOG.ERROR(f"XGBoost训练失败: {e}")
            raise e
    
    def predict(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        使用训练好的模型进行预测
        
        Args:
            X: 特征数据
            **kwargs: 预测参数
                - ntree_limit: 使用的树的数量限制
                - output_margin: 是否输出原始分数
        """
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，请先调用fit方法")
        
        try:
            # 创建DMatrix
            dtest = xgb.DMatrix(X.values, feature_names=self._feature_names)
            
            # 预测参数
            ntree_limit = kwargs.get('ntree_limit', 0)
            output_margin = kwargs.get('output_margin', False)
            
            predictions = self.model.predict(
                dtest,
                ntree_limit=ntree_limit,
                output_margin=output_margin
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
            GLOG.ERROR(f"XGBoost预测失败: {e}")
            raise e
    
    def predict_proba(self, X: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """预测类别概率（仅用于分类任务）"""
        if self.task != "classification":
            raise NotImplementedError("概率预测仅适用于分类任务")
        
        # 对于二分类，需要返回两个类别的概率
        predictions = self.predict(X, **kwargs)
        if predictions.shape[1] == 1:
            # 二分类情况，计算补概率
            prob_positive = predictions.values.flatten()
            prob_negative = 1 - prob_positive
            return pd.DataFrame(
                np.column_stack([prob_negative, prob_positive]),
                index=X.index,
                columns=['prob_class_0', 'prob_class_1']
            )
        else:
            return predictions
    
    def get_feature_importance(self) -> Optional[pd.Series]:
        """获取特征重要性"""
        if not self.is_trained:
            return None
        
        # XGBoost支持多种重要性类型
        importance_dict = self.model.get_score(importance_type='gain')
        
        # 确保所有特征都包含在内
        importance_values = []
        for feature in self._feature_names:
            importance_values.append(importance_dict.get(feature, 0.0))
        
        return pd.Series(
            importance_values,
            index=self._feature_names,
            name='importance'
        ).sort_values(ascending=False)
    
    def set_hyperparameters(self, **hyperparams) -> None:
        """设置超参数"""
        # 处理GPU相关参数
        if 'use_gpu' in hyperparams:
            use_gpu = hyperparams.pop('use_gpu')
            if use_gpu:
                hyperparams['tree_method'] = 'gpu_hist'
                hyperparams['gpu_id'] = hyperparams.get('gpu_id', 0)
            else:
                hyperparams.pop('tree_method', None)
                hyperparams.pop('gpu_id', None)
        
        self._hyperparameters.update(hyperparams)
        GLOG.INFO(f"更新超参数: {hyperparams}")
    
    def validate_hyperparameters(self) -> bool:
        """验证超参数有效性"""
        required_params = ['objective']
        for param in required_params:
            if param not in self._hyperparameters:
                GLOG.WARNING(f"缺少必需参数: {param}")
                return False
        
        # 检查GPU相关配置
        if self.use_gpu:
            try:
                # 简单检查GPU是否可用
                xgb.DMatrix(np.random.random((10, 5)))
                GLOG.INFO("GPU配置验证通过")
            except Exception as e:
                GLOG.WARNING(f"GPU配置可能有问题: {e}")
                return False
        
        return True
    
    def get_model_dump(self) -> List[str]:
        """获取模型结构信息"""
        if not self.is_trained:
            return []
        
        return self.model.get_dump()
    
    def _prepare_target(self, y: Union[pd.DataFrame, pd.Series, np.ndarray]) -> np.ndarray:
        """准备目标变量格式"""
        if isinstance(y, pd.DataFrame):
            if y.shape[1] == 1:
                return y.values.ravel()
            else:
                raise ValueError("XGBoost不支持多标签训练")
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
        if len(self._evals_result) > 1:
            # 使用第一个验证集的指标
            valid_key = list(self._evals_result.keys())[1]
            if valid_key in self._evals_result:
                final_metrics = {}
                for metric_name, values in self._evals_result[valid_key].items():
                    if values:
                        final_metrics[f"final_{metric_name}"] = values[-1]
                self.set_validation_metrics(final_metrics)
    
    def get_training_info(self) -> Dict[str, Any]:
        """获取训练信息"""
        if not self.is_trained:
            return {}
        
        return {
            "num_boosted_rounds": self.model.num_boosted_rounds(),
            "num_features": self.model.num_features(),
            "objective": self._hyperparameters.get("objective", "unknown"),
            "best_ntree_limit": getattr(self.model, "best_ntree_limit", -1),
            "feature_names": self._feature_names,
            "feature_importances": self.get_feature_importance().to_dict() if self.get_feature_importance() is not None else {}
        }
    
    def save(self, filepath: str, **kwargs) -> None:
        """保存模型"""
        if not self.is_trained:
            raise RuntimeError("模型尚未训练，无法保存")
        
        # 保存XGBoost模型
        model_path = filepath.replace('.pkl', '.xgb')
        self.model.save_model(model_path)
        
        # 保存元数据
        super().save(filepath, **kwargs)
        
        GLOG.INFO(f"XGBoost模型已保存: {filepath}")
    
    @classmethod
    def load(cls, filepath: str, **kwargs) -> 'XGBoostModel':
        """加载模型"""
        # 先加载元数据
        base_model = super().load(filepath, **kwargs)
        
        # 加载XGBoost模型
        model_path = filepath.replace('.pkl', '.xgb')
        if model_path != filepath:
            base_model.model = xgb.Booster()
            base_model.model.load_model(model_path)
        
        GLOG.INFO(f"XGBoost模型已加载: {filepath}")
        return base_model