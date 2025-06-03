# Initial code base for the Live-Coding part of the BAIS Advanced Seminar

## Overview

- `/pysolver` contains main access point, including the main file (`__main__.py`).
- `/resources` contains the instances of the simple CVRP problem, which we will focus on. 
- `/routingblocks-bais-as` is a local fork of the [native extension template](https://github.com/tumBAIS/routingblocks-native-extension-example) which we will use and modify.
- `/RoutingBlocks-develop` is a clone of the [routingblocks repository](https://github.com/tumBAIS/routingblocks).

## Getting Started

- Install [Python](https://www.python.org/downloads/) (>=3.11)

### For Windows Users
- Install `cmake` (link: https://cmake.org/download/) and make sure `cmake` is in your system PATH (it should be like: C:\Users\username\cmake-3.31.2-windows-x86_64\bin)
- Run `cmake --version` to confirm you have installed successfully
- Install `C++ compiler` (e.g. [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)  )
- [Link](https://stackoverflow.com/questions/69338088/error-while-configuring-cmake-project-running-nmake-failed) to a possible error you may get -- make sure you successfully followed the steps above

### For Mac Users
- Install `xcode`
  - Open the terminal and run `xcode-select --install`  
  - A dialog will pop up asking you to install the command line tools. Accept and follow the prompts.   
  - Once installed, you can check for successful installation with `clang --version`
- Install `cmake`  
  - Still in the teminal, run `brew install cmake`  
  - Once installed, you can check for successful installation with `cmake --version`
  
- Make sure the plot can be visualized as well:  In PyCharm, go to *Preferences → Tools → Python Scientific* and uncheck "Show plots in tool window"

Run the following commands in the terminal in the root folder of this project:
- `pip install -e RoutingBlocks-develop` (install routingblocks for development)
- `pip install -e routingblocks-bais-as` (install extension)
- `pip install -r pysolver/requirements.txt` (install other packages)
- `python -m pysolver ./resources/instances/Augerat/A-n32-k5.vrp` (run solver)


# Link to excel solver documentation
https://www.sciencedirect.com/science/article/pii/S0305054817300552