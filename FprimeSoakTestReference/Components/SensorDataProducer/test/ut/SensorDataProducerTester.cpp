// ======================================================================
// \title  SensorDataProducerTester.cpp
// \author moisesmata
// \brief  cpp file for SensorDataProducer component test harness implementation class
// ======================================================================

#include "SensorDataProducerTester.hpp"

namespace Components {

SensorDataProducerTester::SensorDataProducerTester()
    : SensorDataProducerGTestBase("SensorDataProducerTester", MAX_HISTORY_SIZE),
      component("SensorDataProducer"),
      m_getStatus(Fw::Success::SUCCESS) {
    this->initComponents();
    this->connectPorts();
}

SensorDataProducerTester::~SensorDataProducerTester() {}

void SensorDataProducerTester::sendStart() {
    this->clearHistory();
    this->sendCmd_START_SERIALIZING(0, 0);
    ASSERT_CMD_RESPONSE_SIZE(1);
    ASSERT_CMD_RESPONSE(0, SensorDataProducer::OPCODE_START_SERIALIZING, 0, Fw::CmdResponse::OK);
    ASSERT_EVENTS_DpProductionStarted_SIZE(1);
    this->clearHistory();
}

void SensorDataProducerTester::sendStop() {
    this->clearHistory();
    this->sendCmd_STOP_SERIALIZING(0, 0);
    ASSERT_CMD_RESPONSE_SIZE(1);
    ASSERT_CMD_RESPONSE(0, SensorDataProducer::OPCODE_STOP_SERIALIZING, 0, Fw::CmdResponse::OK);
    ASSERT_EVENTS_DpProductionStopped_SIZE(1);
}

void SensorDataProducerTester::pushBmp(F32 pressure, F32 temperature) {
    Bmp280::Bmp280Data bmp;
    bmp.set_pressure(pressure);
    bmp.set_temperature(temperature);
    bmp.set_altitude(0.0f);
    this->invoke_to_bmpDataIn(0, bmp);
}

void SensorDataProducerTester::pushImu(F32 temperature) {
    MpuImu::ImuData imu;
    imu.set_temperature(temperature);
    imu.set_acceleration(FprimeSensors::GeometricVector3(1.0f, 2.0f, 3.0f));
    imu.set_rotation(FprimeSensors::GeometricVector3(4.0f, 5.0f, 6.0f));
    this->invoke_to_imuDataIn(0, imu);
}

Fw::Success::T SensorDataProducerTester::productGet_handler(FwDpIdType id, FwSizeType dataSize, Fw::Buffer& buffer) {
    this->pushProductGetEntry(id, dataSize);
    if (Fw::Success::SUCCESS == this->m_getStatus) {
        FW_ASSERT(dataSize <= sizeof(this->m_dpBuffer), static_cast<FwAssertArgType>(dataSize));
        buffer.set(this->m_dpBuffer, dataSize);
    }
    return this->m_getStatus;
}

void SensorDataProducerTester::testInactiveDropsData() {
    this->pushBmp(101000.0f, 25.0f);
    this->pushImu(30.0f);
    ASSERT_PRODUCT_GET_SIZE(0);
    ASSERT_PRODUCT_SEND_SIZE(0);

    this->sendStart();
    this->sendStop();
    this->clearHistory();
    this->pushBmp(101000.0f, 25.0f);
    ASSERT_PRODUCT_GET_SIZE(0);
    ASSERT_PRODUCT_SEND_SIZE(0);
}

void SensorDataProducerTester::testBmpReadingWritesRecord() {
    this->sendStart();
    this->pushBmp(101000.0f, 25.0f);
    ASSERT_PRODUCT_GET_SIZE(1);
    ASSERT_EVENTS_DpStarted_SIZE(1);
    ASSERT_PRODUCT_SEND_SIZE(0);
}

void SensorDataProducerTester::testImuReadingWritesRecord() {
    this->sendStart();
    this->pushImu(30.0f);
    ASSERT_PRODUCT_GET_SIZE(1);
    ASSERT_EVENTS_DpStarted_SIZE(1);
    ASSERT_PRODUCT_SEND_SIZE(0);
}

void SensorDataProducerTester::testContainerSendsWhenFull() {
    this->sendStart();
    for (FwSizeType i = 0; i < SensorDataProducer::RECORD_COUNT; i++) {
        if ((i % 2) == 0) {
            this->pushBmp(101000.0f + static_cast<F32>(i), 25.0f);
        } else {
            this->pushImu(30.0f + static_cast<F32>(i));
        }
    }
    ASSERT_PRODUCT_GET_SIZE(1);
    ASSERT_PRODUCT_SEND_SIZE(1);
    ASSERT_EVENTS_DpComplete_SIZE(1);
    ASSERT_EVENTS_DpComplete(0, static_cast<U32>(SensorDataProducer::RECORD_COUNT));

    this->clearHistory();
    this->pushBmp(101000.0f, 25.0f);
    ASSERT_PRODUCT_GET_SIZE(1);
}

void SensorDataProducerTester::testStopSendsPartialContainer() {
    this->sendStart();
    this->pushBmp(101000.0f, 25.0f);
    this->pushImu(30.0f);
    this->pushImu(31.0f);
    ASSERT_PRODUCT_GET_SIZE(1);
    ASSERT_PRODUCT_SEND_SIZE(0);

    this->sendStop();
    ASSERT_PRODUCT_SEND_SIZE(1);
    ASSERT_EVENTS_DpComplete_SIZE(1);
    ASSERT_EVENTS_DpComplete(0, 3);

    this->sendStop();
    ASSERT_PRODUCT_SEND_SIZE(0);
}

void SensorDataProducerTester::testAllocationFailure() {
    this->sendStart();
    this->m_getStatus = Fw::Success::FAILURE;
    this->pushBmp(101000.0f, 25.0f);
    ASSERT_PRODUCT_GET_SIZE(1);
    ASSERT_PRODUCT_SEND_SIZE(0);
    ASSERT_EVENTS_DpMemoryFail_SIZE(1);
}

}  // namespace Components
