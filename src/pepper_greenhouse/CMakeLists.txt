# Copyright 2026 funfun
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

cmake_minimum_required(VERSION 3.8)
project(pepper_greenhouse)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY worlds models launch config docs
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/generate_world.py scripts/check_layout.py
           scripts/save_camera_frame.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  FILES scripts/layout.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(
    test_generated_assets test/test_generated_assets.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}/scripts
  )
endif()

ament_package()
