// ======================================================================
// \title  SensorDataProducer.hpp
// \author moisesmata
// \brief  hpp file for SensorDataProducer component implementation class
// ======================================================================

#ifndef SensorDataProducer_SensorDataProducer_HPP
#define SensorDataProducer_SensorDataProducer_HPP

#include "FprimeSoakTestReference/Components/SensorDataProducer/SensorDataProducerComponentAc.hpp"

namespace Components {

class SensorDataProducer final : public SensorDataProducerComponentBase {
  public:
    // Must keep RECORD_COUNT * (ImuSensorData + id) under DataProducts
    // dpBufferStoreSize (10000). 100 fits; 500 does not (~23 KB) and causes
    // BufferAllocationFailed + DpMemoryFail floods on RF.
    static constexpr FwSizeType RECORD_COUNT = 100;
    // Keep every Nth sample from each sensor (10 Hz → ~2 Hz each).
    // ~4 records/s → one .fdp every ~25 s when serializing.
    static constexpr U32 SAMPLE_STRIDE = 5;

    SensorDataProducer(const char* const compName);
    ~SensorDataProducer();

  private:
    void bmpDataIn_handler(FwIndexType portNum, const Bmp280::Bmp280Data& data) override;
    void imuDataIn_handler(FwIndexType portNum, const MpuImu::ImuData& data) override;

    void START_SERIALIZING_cmdHandler(FwOpcodeType opCode, U32 cmdSeq) override;
    void STOP_SERIALIZING_cmdHandler(FwOpcodeType opCode, U32 cmdSeq) override;

    //! Allocate a container if needed. Returns true when one is available.
    bool ensureContainer();
    //! Count a written record; send the container when full.
    void recordWritten();
    //! True when this sample should be serialized (stride throttle).
    bool takeSample(U32& counter);

    bool m_active;
    bool m_containerValid;
    bool m_loggedAllocFail;
    FwSizeType m_count;
    U32 m_bmpStride;
    U32 m_imuStride;
    DpContainer m_container;
};

}  // namespace Components

#endif
