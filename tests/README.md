# Slip-Aware Trajectory Planning Test Suite

This directory contains all testing materials for the slip-aware trajectory planning system in the `uneven_planner` package.

## 📁 Directory Structure

```
tests/
├── README.md                    # This file - overview of test suite
├── test_cases.md               # Original test case design document
├── scripts/                    # Test analysis and automation scripts
│   ├── analyze_test_case2.py   # Test Case 2 analysis script
│   └── run_all_tests.py        # Master test automation script (TBD)
├── logs/                       # Raw test execution logs
│   ├── test_case1_ps0_flat.log # Test Case 1 logs (Ps=0, flat terrain)
│   ├── test_case2_ps1_slope.log # Test Case 2 logs (Ps=1, slope terrain)
│   └── test_case3_ps10_slope.log # Test Case 3 logs (Ps=10, slope terrain)
├── reports/                    # Generated test reports and analysis
│   ├── test_case1_final_report.md # Test Case 1 final analysis
│   ├── test_case2_report.md    # Test Case 2 analysis report
│   └── comprehensive_test_summary.md # Overall test suite summary
└── data/                       # Test configuration and reference data
    ├── test_configurations.yaml # Test parameter configurations
    └── reference_trajectories/ # Reference trajectory data for comparison
```

## 🎯 Test Cases Overview

### Test Case 1: Flat Terrain Verification (Ps = 0.0)
- **Objective**: Verify slip cost calculations are zero on flat terrain when disabled
- **Status**: ✅ **COMPLETED**
- **Result**: All slip costs = 0 as expected (Ps=0 disables calculation)
- **Files**: `logs/test_case1_ps0_flat.log`, `reports/test_case1_final_report.md`

### Test Case 2: Slope Terrain with Slip Cost (Ps = 1.0)
- **Objective**: Verify slip cost calculations work correctly on slope terrain
- **Status**: ✅ **COMPLETED**
- **Result**: 448 non-zero slip cost calculations, all KPIs passed
- **Files**: `logs/test_case2_ps1_slope.log`, `scripts/analyze_test_case2.py`

### Test Case 3: High Slip Weight Comparison (Ps = 10.0)
- **Objective**: Compare trajectory behavior with higher slip cost weighting
- **Status**: 🔄 **PLANNED**
- **Expected**: Higher slip costs, potentially different trajectory choices

## 🚀 Quick Start

### Running Analysis Scripts

```bash
# Analyze Test Case 2 results
cd /home/grey/catkin_ws/src/uneven_planner/tests
python3 scripts/analyze_test_case2.py

# Future: Run all tests automatically
# python3 scripts/run_all_tests.py
```

### Test Execution Workflow

1. **Setup Environment**:
   ```bash
   cd /home/grey/catkin_ws
   source devel/setup.bash
   ./src/uneven_planner/hill.sh
   ```

2. **Enable Debug Logging**:
   ```bash
   rosservice call /manager_node/set_logger_level '{logger: "ros", level: "debug"}'
   ```

3. **Start Log Capture**:
   ```bash
   rostopic echo /rosout | grep -E "(ALMTrajOpt.*Slip cost|slip_cost)" > tests/logs/test_case_X.log &
   ```

4. **Execute Planning in RViz** (manual step)

5. **Stop Logging and Analyze**:
   ```bash
   kill %1  # Stop log capture
   python3 tests/scripts/analyze_test_case_X.py
   ```

## 📊 Key Performance Indicators (KPIs)

### KPI 1: Calculation Accuracy
- **Metric**: Percentage of slip cost calculations matching expected formula
- **Target**: >99% accuracy
- **Test Case 2 Result**: ✅ 100% (all calculations verified)

### KPI 2: Parameter Effectiveness
- **Metric**: Proper response to parameter changes (Ps = 0 vs Ps > 0)
- **Target**: Zero costs when Ps=0, non-zero when Ps>0
- **Test Results**: ✅ Verified (TC1: all zero, TC2: all non-zero)

### KPI 3: Terrain Sensitivity
- **Metric**: Non-zero slip costs on slope terrain
- **Target**: Measurable slip costs on slopes with Ps>0
- **Test Case 2 Result**: ✅ 448/448 non-zero costs

### KPI 4: Trajectory Impact (Future)
- **Metric**: Observable trajectory differences with different Ps values
- **Target**: Lower speeds or alternative paths for higher Ps
- **Status**: 🔄 To be measured in Test Case 3

## 🔧 Test Configuration

### Core Parameters
- `temp_param_Ps`: Slip cost weighting parameter (currently hardcoded in C++)
- Target values: 0.0, 1.0, 10.0 for comparative testing

### Test Environment
- **Simulation**: Gazebo with `hill.world`
- **Robot Model**: Original car-like robot model
- **Terrain**: Various slope configurations in hill environment

## 📝 Analysis Tools

### Available Scripts
1. **`analyze_test_case2.py`**: Comprehensive Test Case 2 analysis
   - Parses slip cost debug logs
   - Verifies calculation accuracy
   - Generates statistical analysis
   - Outputs formatted test report

### Future Tools (Planned)
1. **`run_all_tests.py`**: Automated test execution
2. **`compare_trajectories.py`**: Trajectory comparison tool
3. **`generate_test_report.py`**: Comprehensive report generator

## 🏁 Test Status Summary

| Test Case | Parameter | Terrain | Status | Key Result |
|-----------|-----------|---------|--------|------------|
| TC1 | Ps = 0.0 | Flat | ✅ Complete | All slip costs = 0 |
| TC2 | Ps = 1.0 | Slope | ✅ Complete | 448 non-zero costs |
| TC3 | Ps = 10.0 | Slope | 🔄 Planned | Higher slip costs expected |

**Overall Test Suite Status**: 🔄 **In Progress** (2/3 test cases completed)

## 🚨 Known Issues

1. **Log Format Truncation**: ROS debug logs may truncate long lines, requiring parsing adjustments
2. **Parameter Hardcoding**: `temp_param_Ps` currently hardcoded in C++, needs configuration system
3. **Manual Execution**: Test execution requires manual RViz interaction

## 📚 References

- **Test Plan**: `test_cases.md` - Original test case design document
- **Implementation**: `src/uneven_planner/back_end/src/alm_traj_opt.cpp` - Slip cost implementation
- **Environment**: `src/carsim/worlds/map_hill.world` - Test environment definition 