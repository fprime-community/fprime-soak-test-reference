// ======================================================================
// \title  SensorDataProducer.cpp
// \author moisesmata
// \brief  cpp file for SensorDataProducer component implementation class
// ======================================================================

#include "FprimeSoakTestReference/Components/SensorDataProducer/SensorDataProducer.hpp"

namespace Components {

SensorDataProducer::SensorDataProducer(const char* const compName)
    : SensorDataProducerComponentBase(compName),
      m_active(false),
      m_containerValid(false),
      m_loggedAllocFail(false),
      m_count(0),
      m_bmpStride(0),
      m_imuStride(0) {}

SensorDataProducer::~SensorDataProducer() {}

bool SensorDataProducer::takeSample(U32& counter) {
    counter++;
    if (counter < SAMPLE_STRIDE) {
        return false;
    }
    counter = 0;
    return true;
}

bool SensorDataProducer::ensureContainer() {
    if (this->m_containerValid) {
        return true;
    }
    const FwSizeType bmpSize = BmpSensorData::SERIALIZED_SIZE + sizeof(FwDpIdType);
    const FwSizeType imuSize = ImuSensorData::SERIALIZED_SIZE + sizeof(FwDpIdType);
    // Multiply by imuSize as it is bigger
    const FwSizeType dpSize = RECORD_COUNT * imuSize;

    if (this->dpGet_SensorDataContainer(dpSize, this->m_container) != Fw::Success::SUCCESS) {
        // One EVR per outage — not one per sensor tick (that saturates RF).
        if (!this->m_loggedAllocFail) {
            this->log_WARNING_HI_DpMemoryFail();
            this->m_loggedAllocFail = true;
        }
        return false;
    }
    this->m_loggedAllocFail = false;
    this->m_containerValid = true;
    this->m_count = 0;
    this->log_ACTIVITY_LO_DpStarted();
    return true;
}

void SensorDataProducer::recordWritten() {
    this->m_count++;
    if (this->m_count >= RECORD_COUNT) {
        this->log_ACTIVITY_LO_DpComplete(static_cast<U32>(this->m_count));
        this->dpSend(this->m_container);
        this->m_containerValid = false;
        this->m_count = 0;
    }
}

void SensorDataProducer::bmpDataIn_handler(FwIndexType portNum, const Bmp280::Bmp280Data& data) {
    if (!this->m_active || !this->takeSample(this->m_bmpStride) || !this->ensureContainer()) {
        return;
    }
    const Fw::Time t = this->getTime();
    BmpSensorData record;
    record.set_timeTag(Fw::TimeValue(t.getTimeBase(), t.getContext(), t.getSeconds(), t.getUSeconds()));
    record.set_pressure(data.get_pressure());
    record.set_temperature(data.get_temperature());
    record.set_altitude(data.get_altitude());

    FW_ASSERT(this->m_container.serializeRecord_BmpRecord(record) == Fw::FW_SERIALIZE_OK);
    this->recordWritten();
}

void SensorDataProducer::imuDataIn_handler(FwIndexType portNum, const MpuImu::ImuData& data) {
    if (!this->m_active || !this->takeSample(this->m_imuStride) || !this->ensureContainer()) {
        return;
    }
    const Fw::Time t = this->getTime();
    ImuSensorData record;
    record.set_timeTag(Fw::TimeValue(t.getTimeBase(), t.getContext(), t.getSeconds(), t.getUSeconds()));
    record.set_temperature(data.get_temperature());
    record.set_acceleration(data.get_acceleration());
    record.set_rotation(data.get_rotation());

    FW_ASSERT(this->m_container.serializeRecord_ImuRecord(record) == Fw::FW_SERIALIZE_OK);
    this->recordWritten();
}

void SensorDataProducer::START_SERIALIZING_cmdHandler(FwOpcodeType opCode, U32 cmdSeq) {
    this->m_active = true;
    this->m_bmpStride = 0;
    this->m_imuStride = 0;
    this->m_loggedAllocFail = false;
    this->tlmWrite_DpActive(true);
    this->log_ACTIVITY_HI_DpProductionStarted();
    this->cmdResponse_out(opCode, cmdSeq, Fw::CmdResponse::OK);
}

void SensorDataProducer::STOP_SERIALIZING_cmdHandler(FwOpcodeType opCode, U32 cmdSeq) {
    this->m_active = false;
    if (this->m_containerValid) {
        this->log_ACTIVITY_LO_DpComplete(static_cast<U32>(this->m_count));
        this->dpSend(this->m_container);
        this->m_containerValid = false;
    }
    this->m_count = 0;
    this->tlmWrite_DpActive(false);
    this->log_ACTIVITY_HI_DpProductionStopped();
    this->cmdResponse_out(opCode, cmdSeq, Fw::CmdResponse::OK);
}

}  // namespace Components
