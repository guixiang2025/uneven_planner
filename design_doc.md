# uneven_planner 打滑感知轨迹规划设计文档

## 1. 系统概述

### 1.1 设计目标
在 uneven_planner 框架中实现一种显式考虑并缓解车轮打滑的轨迹规划方法，通过将打滑风险转化为优化问题中的成本项，引导规划器生成风险更低的轨迹。

### 1.2 核心思想
- 将打滑风险量化为成本函数
- 在轨迹优化中集成打滑成本
- 通过参数调节平衡各项优化目标

## 2. 系统架构

### 2.1 整体架构
```
+------------------+     +------------------+     +------------------+
|   打滑风险模型    | --> |   轨迹优化模块    | --> |   参数配置模块    |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
+------------------+     +------------------+     +------------------+
|   地形数据处理    |     |   成本计算模块    |     |   ROS参数服务    |
+------------------+     +------------------+     +------------------+
```

### 2.2 模块说明
1. 打滑风险模型
   - 输入：地形数据、速度数据
   - 输出：打滑风险值
   - 功能：计算打滑风险成本

2. 轨迹优化模块
   - 输入：打滑风险、轨迹数据
   - 输出：优化后的轨迹
   - 功能：轨迹优化计算

3. 参数配置模块
   - 输入：ROS参数
   - 输出：配置参数
   - 功能：参数管理和调整

## 3. 详细设计

### 3.1 打滑风险模型

#### 3.1.1 风险计算公式
```cpp
Cost_slip_rate = Ps * (Slope * v)^2
```
其中：
- Ps: 可调节的权重系数
- Slope: 地形坡度
- v: 车辆速度

#### 3.1.2 坡度计算
```cpp
Slope_k_squared = sin_phix_k^2 + sin_phiy_k^2
```
其中：
- sin_phix_k: x方向坡度正弦值
- sin_phiy_k: y方向坡度正弦值

#### 3.1.3 速度计算
```cpp
v_k = v_norm_k * inv_cos_vphix_k
```
其中：
- v_norm_k: 平面速度
- inv_cos_vphix_k: 地形调整因子

### 3.2 轨迹优化集成

#### 3.2.1 成本计算
```cpp
delta_Cost_slip_k = Ps * Slope_k_squared * v_k^2 * step_k
```
其中：
- step_k: 时间步长
- 其他参数同上

#### 3.2.2 优化流程
1. 轨迹离散化
2. 计算每个点的打滑成本
3. 累加得到总成本
4. 优化器调整轨迹

### 3.3 代码实现

#### 3.3.1 类设计
```cpp
class ALMTrajOpt {
private:
    double param_Ps_slip_weight;  // 打滑权重系数
    
public:
    // 初始化参数
    void init() {
        nh.getParam("alm_traj_opt/Ps_slip_weight", param_Ps_slip_weight);
    }
    
    // 计算约束成本
    void calConstrainCostGrad() {
        // 实现打滑成本计算
    }
};
```

#### 3.3.2 关键函数实现
```cpp
void ALMTrajOpt::calConstrainCostGrad() {
    // 遍历轨迹段
    for (auto& piece_xy : traj_xy) {
        // 遍历采样点
        for (int k = 0; k < num_samples; k++) {
            // 获取地形数据
            getTerrainVariables(se2_pos_k, terrain_values_k);
            
            // 计算坡度
            double sin_phix_k = terrain_values_k[1];
            double sin_phiy_k = terrain_values_k[3];
            double slope_k_squared = sin_phix_k * sin_phix_k + 
                                   sin_phiy_k * sin_phiy_k;
            
            // 计算速度
            double v_norm_k = vel_k.norm();
            double inv_cos_vphix_k = terrain_values_k[0];
            double v_k = v_norm_k * inv_cos_vphix_k;
            
            // 计算打滑成本
            double delta_cost_slip_k = param_Ps_slip_weight * 
                                     slope_k_squared * 
                                     v_k * v_k * 
                                     step_k;
            
            // 累加成本
            cost += delta_cost_slip_k;
        }
    }
}
```

## 4. 参数配置

### 4.1 ROS参数
```yaml
alm_traj_opt:
  Ps_slip_weight: 1.0  # 打滑权重系数
```

### 4.2 参数说明
- Ps_slip_weight: 控制打滑风险在总成本中的权重
  - 值越大，规划器越倾向于避开高坡度或高速通过坡度的区域
  - 值越小，打滑风险对轨迹规划的影响越小

## 5. 测试方案

### 5.1 单元测试
1. 打滑风险模型测试
   - 测试不同地形条件下的风险计算
   - 测试不同速度下的风险计算
   - 测试参数调整的效果

2. 轨迹优化测试
   - 测试成本计算准确性
   - 测试优化效果
   - 测试计算效率

### 5.2 集成测试
1. 仿真场景测试
   - 标准地形测试
   - 极端地形测试
   - 复杂地形测试

2. 对比实验
   - 实验组A：Ps = 0.0
   - 实验组B：Ps > 0.0
   - 分析轨迹差异

## 6. 性能优化

### 6.1 计算优化
1. 并行计算
   - 轨迹段并行处理
   - 采样点并行计算

2. 内存优化
   - 避免重复计算
   - 优化数据结构

### 6.2 算法优化
1. 梯度计算
   - 实现解析梯度
   - 优化数值梯度

2. 收敛性优化
   - 调整优化参数
   - 改进优化策略

## 7. 部署说明

### 7.1 环境要求
- ROS版本：Noetic或更高
- 依赖包：
  - uneven_planner
  - Gazebo
  - 其他必要依赖

### 7.2 部署步骤
1. 代码部署
   ```bash
   cd ~/catkin_ws/src
   git clone [repository_url]
   cd ..
   catkin_make
   ```

2. 参数配置
   - 修改ROS参数文件
   - 调整打滑权重系数

3. 启动测试
   ```bash
   roslaunch uneven_planner test_slip_aware.launch
   ```

## 8. 维护计划

### 8.1 日常维护
- 代码审查
- 性能监控
- 问题修复

### 8.2 版本更新
- 功能增强
- 性能优化
- 文档更新

## 9. 附录

### 9.1 术语表
- 打滑风险：车辆在特定地形和速度下的打滑可能性
- 轨迹优化：调整轨迹以最小化总成本的过程
- 成本函数：用于评估轨迹质量的数学表达式

### 9.2 参考文档
- uneven_planner 框架文档
- ROS 参数服务器文档
- 轨迹优化算法文档 