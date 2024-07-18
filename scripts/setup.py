from cx_Freeze import setup, Executable
import os

build_exe_options = {
    "packages": ["os", "time", "logging", "subprocess", "datetime", "socket", "json"],
    "excludes": ["tkinter"],
    "include_files": [
        # Add paths to any additional required files or DLLs here, if necessary
        # For example:
        # os.path.join(os.environ['WINDIR'], 'System32', 'api-ms-win-core-path-l1-1-0.dll'),
    ]
}

setup(
    name="serviceMonitor",
    version="1.0",
    description="Service Monitor",
    options={"build_exe": build_exe_options},
    executables=[Executable("serverservicemon.py", base="Win32GUI")]
)
