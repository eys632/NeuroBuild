cmake_minimum_required(VERSION 3.23)
set(CMAKE_C_COMPILER "/usr/local/bin/gcc" CACHE FILEPATH "" FORCE)
set(CMAKE_CXX_COMPILER "/usr/local/bin/g++" CACHE FILEPATH "" FORCE)
project(neurobuild_native_contract_validator LANGUAGES C CXX)
if(NOT CMAKE_C_COMPILER_VERSION STREQUAL "9.5.0" OR
   NOT CMAKE_CXX_COMPILER_VERSION STREQUAL "9.5.0")
  message(FATAL_ERROR "Only the inspected local GCC/G++ 9.5.0 pair is allowed")
endif()

# DRAFT: root must review before configure/build. No upstream file is modified.
set(PIN "f072b103714dfa1eee531f80b24512faf38e3dd2")
get_filename_component(NB_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
set(LLAMA_SOURCE "${NB_ROOT}/var/runtime-src/llama.cpp-${PIN}")
if(NOT EXISTS "${LLAMA_SOURCE}/common/chat.cpp")
  message(FATAL_ERROR "Pinned source is missing")
endif()
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(GGML_BACKEND_DL OFF CACHE BOOL "" FORCE)
set(GGML_CPU ON CACHE BOOL "" FORCE)
foreach(flag CUDA MUSA HIP VULKAN WEBGPU ZDNN VIRTGPU VIRTGPU_BACKEND METAL
             RPC SYCL OPENVINO ET ET_SYSEMU OPENCL HEXAGON ZENDNN BLAS ACCELERATE
             CPU_KLEIDIAI CPU_HBM OPENMP OPENMP_FETCH CPU_ALL_VARIANTS
             NATIVE CCACHE LTO LLAMAFILE)
  set(GGML_${flag} OFF CACHE BOOL "" FORCE)
endforeach()
set(LLAMA_BUILD_COMMON ON CACHE BOOL "" FORCE)
# Define server-context through unchanged upstream CMake; build only our target,
# never `all`, llama-server, UI assets, or installation targets.
set(LLAMA_BUILD_TOOLS ON CACHE BOOL "" FORCE)
set(LLAMA_BUILD_SERVER ON CACHE BOOL "" FORCE)
foreach(flag BUILD_TESTS BUILD_EXAMPLES BUILD_APP BUILD_UI USE_PREBUILT_UI
             OPENSSL SUBPROCESS LLGUIDANCE TOOLS_INSTALL TESTS_INSTALL)
  set(LLAMA_${flag} OFF CACHE BOOL "" FORCE)
endforeach()
set(FETCHCONTENT_FULLY_DISCONNECTED ON CACHE BOOL "" FORCE)
set(FETCHCONTENT_UPDATES_DISCONNECTED ON CACHE BOOL "" FORCE)
set(LLAMA_BUILD_COMMIT "${PIN}" CACHE STRING "" FORCE)
set(LLAMA_BUILD_NUMBER 0 CACHE STRING "" FORCE)
add_subdirectory("${LLAMA_SOURCE}" "${CMAKE_BINARY_DIR}/llama" EXCLUDE_FROM_ALL)

add_executable(nb-native-contract-validator validator.cpp)
target_compile_features(nb-native-contract-validator PRIVATE cxx_std_17)
target_include_directories(nb-native-contract-validator PRIVATE
  "${LLAMA_SOURCE}/src" "${LLAMA_SOURCE}/common"
  "${LLAMA_SOURCE}/tools/server" "${LLAMA_SOURCE}/tools/mtmd")
target_link_libraries(nb-native-contract-validator PRIVATE server-context llama-common llama)
