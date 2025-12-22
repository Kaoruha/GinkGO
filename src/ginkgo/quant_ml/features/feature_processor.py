"""
特征处理器

提供统一的特征工程接口，支持：
- 数据标准化和归一化
- 缺失值处理
- 特征选择
- 时序特征构建
- 与ginkgo数据格式的无缝集成
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime, timedelta

try:
    from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
    from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
    from sklearn.impute import SimpleImputer, KNNImputer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from ginkgo.libs import GLOG
from ginkgo import services


class FeatureProcessor:
    """
    特征处理器
    
    提供完整的特征工程流水线，支持ginkgo数据格式
    """
    
    def __init__(self, 
                 scaling_method: str = "standard",
                 imputation_method: str = "mean",
                 feature_selection: bool = False,
                 n_features: Optional[int] = None):
        """
        初始化特征处理器
        
        Args:
            scaling_method: 标准化方法 ("standard", "minmax", "robust", "none")
            imputation_method: 缺失值处理方法 ("mean", "median", "mode", "knn", "drop")
            feature_selection: 是否进行特征选择
            n_features: 选择的特征数量
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn未安装，特征处理功能不可用")
        
        self.scaling_method = scaling_method
        self.imputation_method = imputation_method
        self.feature_selection = feature_selection
        self.n_features = n_features
        
        # 处理器对象
        self.scaler = None
        self.imputer = None
        self.selector = None
        
        # 特征信息
        self.feature_names_ = []
        self.selected_features_ = []
        self.is_fitted = False
        
        self._init_processors()
        
        GLOG.INFO(f"初始化特征处理器: 标准化={scaling_method}, 缺失值={imputation_method}")
    
    def _init_processors(self):
        """初始化处理器组件"""
        # 标准化器
        if self.scaling_method == "standard":
            self.scaler = StandardScaler()
        elif self.scaling_method == "minmax":
            self.scaler = MinMaxScaler()
        elif self.scaling_method == "robust":
            self.scaler = RobustScaler()
        elif self.scaling_method == "none":
            self.scaler = None
        else:
            raise ValueError(f"不支持的标准化方法: {self.scaling_method}")
        
        # 缺失值处理器
        if self.imputation_method in ["mean", "median"]:
            self.imputer = SimpleImputer(strategy=self.imputation_method)
        elif self.imputation_method == "mode":
            self.imputer = SimpleImputer(strategy="most_frequent")
        elif self.imputation_method == "knn":
            self.imputer = KNNImputer()
        elif self.imputation_method == "drop":
            self.imputer = None
        else:
            raise ValueError(f"不支持的缺失值处理方法: {self.imputation_method}")
        
        # 特征选择器
        if self.feature_selection and self.n_features:
            self.selector = SelectKBest(score_func=f_regression, k=self.n_features)
    
    def fit(self, X: pd.DataFrame, y: Optional[pd.DataFrame] = None) -> 'FeatureProcessor':
        """
        拟合特征处理器
        
        Args:
            X: 特征数据
            y: 目标变量（特征选择时需要）
        """
        try:
            GLOG.INFO(f"拟合特征处理器，输入特征数: {X.shape[1]}, 样本数: {X.shape[0]}")
            
            self.feature_names_ = list(X.columns)
            X_processed = X.copy()
            
            # 处理缺失值
            if self.imputer is not None:
                X_processed = pd.DataFrame(
                    self.imputer.fit_transform(X_processed),
                    index=X_processed.index,
                    columns=X_processed.columns
                )
                GLOG.DEBUG("完成缺失值处理")
            elif self.imputation_method == "drop":
                X_processed = X_processed.dropna()
                GLOG.DEBUG(f"删除缺失值后样本数: {X_processed.shape[0]}")
            
            # 标准化
            if self.scaler is not None:
                X_processed = pd.DataFrame(
                    self.scaler.fit_transform(X_processed),
                    index=X_processed.index,
                    columns=X_processed.columns
                )
                GLOG.DEBUG("完成数据标准化")
            
            # 特征选择
            if self.selector is not None and y is not None:
                y_array = self._prepare_target(y)
                X_selected = self.selector.fit_transform(X_processed, y_array)
                
                # 获取选中的特征
                selected_mask = self.selector.get_support()
                self.selected_features_ = [
                    feat for i, feat in enumerate(self.feature_names_) if selected_mask[i]
                ]
                
                GLOG.INFO(f"特征选择完成，选中特征数: {len(self.selected_features_)}")
            else:
                self.selected_features_ = self.feature_names_
            
            self.is_fitted = True
            GLOG.INFO("特征处理器拟合完成")
            
            return self
            
        except Exception as e:
            GLOG.ERROR(f"特征处理器拟合失败: {e}")
            raise e
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        转换特征数据
        
        Args:
            X: 输入特征数据
            
        Returns:
            pd.DataFrame: 处理后的特征数据
        """
        if not self.is_fitted:
            raise RuntimeError("特征处理器尚未拟合，请先调用fit方法")
        
        try:
            X_processed = X.copy()
            
            # 确保特征顺序一致
            missing_features = set(self.feature_names_) - set(X.columns)
            if missing_features:
                GLOG.WARN(f"缺少特征: {missing_features}")
            
            # 只保留训练时的特征
            available_features = [f for f in self.feature_names_ if f in X.columns]
            X_processed = X_processed[available_features]
            
            # 处理缺失值
            if self.imputer is not None:
                X_processed = pd.DataFrame(
                    self.imputer.transform(X_processed),
                    index=X_processed.index,
                    columns=X_processed.columns
                )
            elif self.imputation_method == "drop":
                X_processed = X_processed.dropna()
            
            # 标准化
            if self.scaler is not None:
                X_processed = pd.DataFrame(
                    self.scaler.transform(X_processed),
                    index=X_processed.index,
                    columns=X_processed.columns
                )
            
            # 特征选择
            if self.selector is not None:
                X_selected = pd.DataFrame(
                    self.selector.transform(X_processed),
                    index=X_processed.index,
                    columns=self.selected_features_
                )
                return X_selected
            
            return X_processed
            
        except Exception as e:
            GLOG.ERROR(f"特征转换失败: {e}")
            raise e
    
    def fit_transform(self, X: pd.DataFrame, y: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """拟合并转换特征数据"""
        return self.fit(X, y).transform(X)
    
    def create_time_features(self, df: pd.DataFrame, 
                           datetime_col: str = 'timestamp',
                           lookback_periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
        """
        创建时序特征
        
        Args:
            df: 输入数据（需包含时间列）
            datetime_col: 时间列名
            lookback_periods: 回看期列表
            
        Returns:
            pd.DataFrame: 增加时序特征的数据
        """
        try:
            result_df = df.copy()
            
            if datetime_col not in df.columns:
                GLOG.WARN(f"未找到时间列 {datetime_col}，跳过时序特征创建")
                return result_df
            
            # 确保时间列为datetime类型
            if not pd.api.types.is_datetime64_any_dtype(result_df[datetime_col]):
                result_df[datetime_col] = pd.to_datetime(result_df[datetime_col])
            
            # 按时间排序
            result_df = result_df.sort_values(datetime_col)
            
            # 数值列
            numeric_cols = result_df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                # 滚动统计特征
                for period in lookback_periods:
                    # 移动平均
                    result_df[f'{col}_ma_{period}'] = result_df[col].rolling(
                        window=period, min_periods=1
                    ).mean()
                    
                    # 移动标准差
                    result_df[f'{col}_std_{period}'] = result_df[col].rolling(
                        window=period, min_periods=1
                    ).std()
                    
                    # 价格相对位置
                    rolling_min = result_df[col].rolling(window=period, min_periods=1).min()
                    rolling_max = result_df[col].rolling(window=period, min_periods=1).max()
                    result_df[f'{col}_position_{period}'] = (
                        (result_df[col] - rolling_min) / (rolling_max - rolling_min + 1e-8)
                    )
                
                # 变化率特征
                result_df[f'{col}_pct_change_1'] = result_df[col].pct_change(1)
                result_df[f'{col}_pct_change_5'] = result_df[col].pct_change(5)
                
                # 价格动量
                result_df[f'{col}_momentum_5'] = result_df[col] / result_df[col].shift(5) - 1
                result_df[f'{col}_momentum_20'] = result_df[col] / result_df[col].shift(20) - 1
            
            # 填充无穷值和缺失值
            result_df = result_df.replace([np.inf, -np.inf], np.nan)
            
            GLOG.INFO(f"创建时序特征完成，新增特征数: {result_df.shape[1] - df.shape[1]}")
            
            return result_df
            
        except Exception as e:
            GLOG.ERROR(f"时序特征创建失败: {e}")
            raise e
    
    def load_ginkgo_data(self, 
                        codes: List[str],
                        start_date: str,
                        end_date: str,
                        adjusted: bool = True) -> pd.DataFrame:
        """
        从ginkgo数据源加载数据
        
        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjusted: 是否使用复权数据
            
        Returns:
            pd.DataFrame: 加载的数据
        """
        try:
            all_data = []
            
            for code in codes:
                # 使用DI架构获取数据服务
                bar_service = services.data.bar_service()
                bars = bar_service.get_bars_filtered(
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                    adjusted=adjusted
                )
                
                if bars:
                    # 转换为DataFrame
                    data_list = []
                    for bar in bars:
                        data_list.append({
                            'code': code,
                            'timestamp': bar.timestamp,
                            'open': bar.open,
                            'high': bar.high,
                            'low': bar.low,
                            'close': bar.close,
                            'volume': bar.volume,
                            'amount': bar.amount if hasattr(bar, 'amount') else 0
                        })
                    
                    df = pd.DataFrame(data_list)
                    all_data.append(df)
            
            if all_data:
                result = pd.concat(all_data, ignore_index=True)
                result['timestamp'] = pd.to_datetime(result['timestamp'])
                
                GLOG.INFO(f"加载数据完成，股票数: {len(codes)}, 记录数: {len(result)}")
                return result
            else:
                GLOG.WARN("未加载到任何数据")
                return pd.DataFrame()
                
        except Exception as e:
            GLOG.ERROR(f"数据加载失败: {e}")
            raise e
    
    def prepare_ml_dataset(self,
                          df: pd.DataFrame,
                          target_col: str,
                          feature_cols: Optional[List[str]] = None,
                          test_size: float = 0.2,
                          time_col: str = 'timestamp') -> Dict[str, pd.DataFrame]:
        """
        准备机器学习数据集
        
        Args:
            df: 原始数据
            target_col: 目标变量列名
            feature_cols: 特征列名列表（为None时自动选择）
            test_size: 测试集比例
            time_col: 时间列名
            
        Returns:
            Dict: 包含训练集和测试集的字典
        """
        try:
            # 特征列选择
            if feature_cols is None:
                # 自动选择数值特征，排除目标变量和时间列
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                feature_cols = [col for col in numeric_cols 
                              if col != target_col and col != time_col]
            
            # 确保所有列都存在
            missing_cols = set([target_col] + feature_cols) - set(df.columns)
            if missing_cols:
                raise ValueError(f"缺少列: {missing_cols}")
            
            # 删除包含缺失值的行
            data_clean = df[[time_col] + feature_cols + [target_col]].dropna()
            
            # 按时间排序
            if time_col in data_clean.columns:
                data_clean = data_clean.sort_values(time_col)
            
            # 时间序列分割（避免数据泄露）
            split_idx = int(len(data_clean) * (1 - test_size))
            
            train_data = data_clean.iloc[:split_idx]
            test_data = data_clean.iloc[split_idx:]
            
            # 构建返回结果
            result = {
                'X_train': train_data[feature_cols],
                'y_train': train_data[[target_col]],
                'X_test': test_data[feature_cols],
                'y_test': test_data[[target_col]]
            }
            
            if time_col in data_clean.columns:
                result['train_time'] = train_data[time_col]
                result['test_time'] = test_data[time_col]
            
            GLOG.INFO(f"数据集准备完成，训练集: {len(train_data)}, 测试集: {len(test_data)}")
            GLOG.INFO(f"特征数: {len(feature_cols)}, 目标变量: {target_col}")
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"数据集准备失败: {e}")
            raise e
    
    def _prepare_target(self, y: Union[pd.DataFrame, pd.Series, np.ndarray]) -> np.ndarray:
        """准备目标变量格式"""
        if isinstance(y, pd.DataFrame):
            return y.values.ravel() if y.shape[1] == 1 else y.values
        elif isinstance(y, pd.Series):
            return y.values
        elif isinstance(y, np.ndarray):
            return y
        else:
            return np.array(y)
    
    def get_feature_info(self) -> Dict[str, Any]:
        """获取特征处理信息"""
        return {
            'is_fitted': self.is_fitted,
            'scaling_method': self.scaling_method,
            'imputation_method': self.imputation_method,
            'feature_selection': self.feature_selection,
            'n_features': self.n_features,
            'original_features': len(self.feature_names_),
            'selected_features': len(self.selected_features_),
            'feature_names': self.feature_names_,
            'selected_feature_names': self.selected_features_
        }