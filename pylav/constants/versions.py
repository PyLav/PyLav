from __future__ import annotations

from packaging.version import Version

from pylav.constants.node import MAX_SUPPORTED_API_MAJOR_VERSION

VERSION_0_0_0 = Version("0.0.0")
VERSION_3_6_0 = Version("3.6.0")
VERSION_3_7_0 = Version("3.7.0")
VERSION_4_0_0 = Version("4.0.0")
VERSION_5_0_0 = Version("5.0.0")

VERSION_3_7_0_FIRST = Version("3.7.0-alpha.dev")
VERSION_4_0_0_FIRST = Version("4.0.0-alpha.dev")
VERSION_5_0_0_FIRST = Version("5.0.0-alpha.dev")

API_DEVELOPMENT_VERSION = Version(f"{MAX_SUPPORTED_API_MAJOR_VERSION}.999.0-alpha")

# Migration versions
VERSION_0_0_0_2 = Version("0.0.0.post2.dev0")
VERSION_0_3_2_0 = Version("0.3.2.dev")
VERSION_0_3_3_0 = Version("0.3.3.dev")
VERSION_0_3_4_0 = Version("0.3.4.dev")
VERSION_0_3_5_0 = Version("0.3.5.dev")
VERSION_0_3_6_0 = Version("0.3.6.dev")
VERSION_0_7_6_0 = Version("0.7.6.dev")
VERSION_0_8_5_0 = Version("0.8.5.dev")
VERSION_0_8_8_0 = Version("0.8.8.dev")
VERSION_0_9_2_0 = Version("0.9.2.dev")
VERSION_0_10_5_0 = Version("0.10.5.dev")
VERSION_0_11_3_0 = Version("0.11.3.dev")
VERSION_0_11_8_0 = Version("0.11.8.dev")
VERSION_1_0_0 = Version("1.0.0.dev")
VERSION_1_1_17 = Version("1.1.17.dev")
VERSION_1_10_0 = Version("1.10.0.dev")
VERSION_1_10_1 = Version("1.10.1.dev")
VERSION_1_12_0 = Version("1.12.0.dev")
VERSION_1_14_0 = Version("1.14.0.dev")
