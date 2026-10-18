#!/usr/bin/env python3
"""Backport KernelSU-Next UAPI v5 (EVENT_SERVICES) into an in-tree driver.

Usage: apply_uapi5.py [repo_root]
Default repo_root is the current directory.

Touches only:
  drivers/kernelsu/include/uapi/supercall.h
  drivers/kernelsu/supercall/dispatch.c
Both changes are additive, so SUSFS integration is preserved.
"""
import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
base = root / "drivers/kernelsu"

# ---- 1) uapi/supercall.h: bump version + add EVENT_SERVICES ----
p = base / "include/uapi/supercall.h"
s = p.read_text()
orig = s
s = s.replace(
    "// 4: add KSU_GET_INFO_FLAG_BUNDLED\nstatic const __u32 KERNEL_SU_UAPI_VERSION = 4;",
    "// 4: add KSU_GET_INFO_FLAG_BUNDLED\n"
    "// 5: add EVENT_SERVICES with a start/skip result\n"
    "static const __u32 KERNEL_SU_UAPI_VERSION = 5;",
)
s = s.replace(
    "static const __u32 EVENT_MODULE_MOUNTED = 3;",
    "static const __u32 EVENT_MODULE_MOUNTED = 3;\n"
    "static const __u32 EVENT_SERVICES = 4;",
)
if s == orig:
    raise SystemExit("ERROR: supercall.h was not modified (pattern not found)")
p.write_text(s)

# ---- 2) supercall/dispatch.c: handle EVENT_SERVICES ----
p = base / "supercall/dispatch.c"
s = p.read_text()
orig = s
if "EVENT_SERVICES" in s:
    raise SystemExit("ERROR: dispatch.c already patched")
s = s.replace(
    "static int do_report_event(void __user *arg)\n{\n\tstruct ksu_report_event_cmd cmd;",
    "static int do_report_event(void __user *arg)\n{\n"
    "\tstatic bool services_started = false;\n\tstruct ksu_report_event_cmd cmd;",
)
s = s.replace(
    "\tcase EVENT_POST_FS_DATA: {\n\t\tstatic bool post_fs_data_lock = false;\n",
    "\tcase EVENT_POST_FS_DATA: {\n\t\tstatic bool post_fs_data_lock = false;\n\n"
    "\t\t// Reset for emulated soft reboot\n\t\tservices_started = false;\n",
)
s = s.replace(
    "\tcase EVENT_MODULE_MOUNTED: {\n\t\tpr_info(\"module mounted!\\n\");\n"
    "\t\ton_module_mounted();\n\t\tbreak;\n\t}\n\tdefault:",
    "\tcase EVENT_MODULE_MOUNTED: {\n\t\tpr_info(\"module mounted!\\n\");\n"
    "\t\ton_module_mounted();\n\t\tbreak;\n\t}\n"
    "\tcase EVENT_SERVICES: {\n"
    "\t\tif (services_started) {\n"
    "\t\t\tpr_info(\"services already started, skipping\\n\");\n"
    "\t\t\treturn 0;\n"
    "\t\t}\n"
    "\t\tservices_started = true;\n"
    "\t\tpr_info(\"services triggered\\n\");\n"
    "\t\treturn 1;\n"
    "\t}\n\tdefault:",
)
if s == orig:
    raise SystemExit("ERROR: dispatch.c was not modified (pattern not found)")
p.write_text(s)

print("OK: UAPI 5 backport applied")
