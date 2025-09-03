# HFVRP Solver – BAIS Advanced Seminar

## Overview

This repository contains the code base developed for the **BAIS Advanced Seminar on Advanced Optimization**.  
The goal of the project is to implement and evaluate a heuristic framework for solving **Heterogeneous Fleet Vehicle Routing Problems (HFVRP)** under realistic conditions.  
Unlike simplified VRP benchmarks, this project integrates:

- **Fleet heterogeneity** (ICEVs, BEVs, leased vehicles, initial fleets with sunk acquisition costs)  
- **Detailed cost modeling** (fuel, electricity, maintenance, wages, tolls, amortized acquisition, penalties)  
- **Policy scenarios** (urban toll regimes, green vehicle incentives, fleet restrictions)  
- **Metaheuristic optimization** (Savings heuristic, Large Neighborhood Search, Iterated Local Search)  

The framework is applied to realistic **case study instances** (Paris, New York, Shanghai) to analyze routing efficiency, fleet selection, and policy impacts.

---

## Repository Structure

- `/pysolver`  
  Main access point of the solver, including the driver script (`__main__.py`) and experiment logic (`main.py`).  
  Handles instance loading, experiment setup, and integration with the C++ evaluation module.

- `/resources`  
  Contains benchmark instances.  
  - Classical CVRP test sets (Augerat, etc.)  
  - Extended HFVRP instances for Paris, New York, Shanghai (`.vrp` files with fleet/city configs and distance data).  

- `/routingblocks-bais-as`  
  Local fork of the [RoutingBlocks native extension template](https://github.com/tumBAIS/routingblocks-native-extension-example).  
  Contains the custom **HFVRP evaluation module** (`evaluation.cpp`) that implements the cost function, feasibility checks, and vehicle assignment logic.

- `/RoutingBlocks-develop`  
  Clone of the [RoutingBlocks repository](https://github.com/tumBAIS/routingblocks).  
  Provides the generic VRP framework and native C++ core used by our extension.

---

## Getting Started

### Requirements

- [Python](https://www.python.org/downloads/) >= 3.11  
- `cmake` and a working C++ compiler toolchain (see platform-specific instructions below)  

### For Windows Users
1. Install [CMake](https://cmake.org/download/) and add it to your system PATH.  
   - Test with: `cmake --version`  
2. Install a C++ compiler (e.g. [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)).  
3. If you run into issues during build, see [this StackOverflow post](https://stackoverflow.com/questions/69338088/error-while-configuring-cmake-project-running-nmake-failed).  

### For Mac Users
1. Install Xcode command line tools:  
   ```bash
   xcode-select --install
2. Install CMAKE vis homebrew:
   ```bash
   brew install cmake

### Installation

Install routingblocks core
- pip install -e RoutingBlocks-develop

Install HFVRP evaluation extension
- pip install -e routingblocks-bais-as

Install Python dependencies
- pip install -r pysolver/requirements.txt

## Running the Solver

### Classical CVRP benchmark
python -m pysolver ./resources/instances/Augerat/A-n32-k5.vrp

### HFVRP case study instances
- python -m pysolver ./resources/instances/test_instances/paris.vrp
- python -m pysolver ./resources/instances/test_instances/newyork.vrp
- python -m pysolver ./resources/instances/test_instances/shanghai.vrp

