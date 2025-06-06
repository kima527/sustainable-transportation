# Copyright (c) 2023 Patrick S. Klein (@libklein)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

cmake_minimum_required(VERSION 3.31)
include(CheckIPOSupported)
include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/CPM.cmake)
# To force building for a specific python version, set Python_ROOT_DIR to the respective path.
# This can be a venv as well.
# See the FIND_PACKAGE python cmake documentation for details.
FIND_PACKAGE(Python COMPONENTS Interpreter Development.Module REQUIRED)

message(STATUS "Found python binary: ${Python_EXECUTABLE} (Version ${Python_VERSION})")

set(PYBIND11_PYTHON_VERSION ${Python_VERSION})
set(PYTHON_EXECUTABLE ${Python_EXECUTABLE})
set(PYTHON_LIBS ${Python_LIBS})

CPMAddPackage(
        NAME pybind11
        GITHUB_REPOSITORY pybind/pybind11
        GIT_TAG archive/smart_holder
)

file(GLOB_RECURSE headers CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/include/routingblocks_bindings/*.h")
file(GLOB_RECURSE sources CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")

pybind11_add_module(${PROJECT_NAME} ${sources})

target_include_directories(${PROJECT_NAME} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_definitions(${PROJECT_NAME} PUBLIC "routingblocks_MODULE_NAME=${PROJECT_NAME}")
target_compile_definitions(${PROJECT_NAME} PUBLIC "routingblocks_VERSION=${PROJECT_VERSION}")
target_compile_definitions(${PROJECT_NAME} PUBLIC "PYBIND11_USE_SMART_HOLDER_AS_DEFAULT")

# Configure optimization flags
if (CMAKE_COMPILER_IS_GNUCC)
    target_compile_options(${PROJECT_NAME} PUBLIC "$<$<CONFIG:DEBUG>:-O0;-g3>")
    target_compile_options(${PROJECT_NAME} PUBLIC "$<$<CONFIG:RELEASE>:-O3;>")
    target_compile_options(${PROJECT_NAME} PUBLIC "$<$<CONFIG:PROFILE>:-O2;-pg;-fno-omit-frame-pointer;-fno-optimize-sibling-calls;>")
endif ()
if (MSVC)
    target_compile_options(${PROJECT_NAME} PUBLIC "$<$<CONFIG:DEBUG>:/Od>")
    target_compile_options(${PROJECT_NAME} PUBLIC "$<$<CONFIG:RELEASE>:/O2y>")
endif ()

# Link to main routing blocks library
target_link_libraries(${PROJECT_NAME} PUBLIC routingblocks)

check_ipo_supported(RESULT ${PROJECT_NAME}_HAS_LTO)
if (${${PROJECT_NAME}_HAS_LTO})
    message(STATUS "LTO is supported")
    set_target_properties(${PROJECT_NAME} PROPERTIES INTERPROCEDUAL_OPTIMIZATION TRUE)
endif ()

#
# Set the compiler standard
#
target_compile_features(${PROJECT_NAME} PUBLIC cxx_std_20)

# Create stub file
file(GLOB stub_files CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/stubs/*.pyi")

add_custom_command(
        OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/_routingblocks.pyi
        COMMAND ${CMAKE_COMMAND} -E echo "Concatenating files..."
        COMMAND ${CMAKE_COMMAND} -E cat ${stub_files} > "${CMAKE_CURRENT_BINARY_DIR}/_routingblocks.pyi"
        DEPENDS ${stub_files}
)

add_custom_target(stub_file ALL DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/_routingblocks.pyi)
add_dependencies(${PROJECT_NAME} stub_file)

INSTALL(TARGETS routingblocks DESTINATION routingblocks)
INSTALL(FILES ${CMAKE_CURRENT_SOURCE_DIR}/include/routingblocks_bindings/binding_helpers.hpp DESTINATION routingblocks/include/routingblocks/)
INSTALL(FILES ${CMAKE_CURRENT_BINARY_DIR}/_routingblocks.pyi DESTINATION routingblocks/)
