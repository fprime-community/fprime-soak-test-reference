####
# FprimeSoakTestReference/project/config/CMakeLists.txt:
#
# Configuration overrides for F Prime subtopologies and components.
# This enables TlmPacketizer instead of TlmChan for the CdhCore subtopology.
# ComCfg/FpConstants are sized for a single RFM69 radio packet (255-byte TM).
# The framework default AcConstants are used as-is; the default
# RateGroupDriverRateGroupPorts of 3 matches the deployment's three rate
# groups driven by RateGroupDriver (1KHz / 10Hz / 1Hz).
####
register_fprime_config(
    CONFIGURATION_OVERRIDES
        "${CMAKE_CURRENT_LIST_DIR}/CdhCoreTlmConfig.fpp"
        "${CMAKE_CURRENT_LIST_DIR}/ComCfg.fpp"
        "${CMAKE_CURRENT_LIST_DIR}/FpConstants.fpp"
        "${CMAKE_CURRENT_LIST_DIR}/AcConstants.fpp"
    INTERFACE
)
