telemetry packets FprimeSoakTestReferenceDeploymentPackets {

  # Group 1 = default radio load (setPacketList level 1). Keep lean for 19.2 kbps.
  packet SensorMediumRate id 3 group 2 {
    FprimeSoakTestReference.sensorDataProducer.DpActive
  }

  # Lean group-1 CDH for radio soak: queue depth + cmd/health timing only.
  packet CDH id 1 group 1 {
    CdhCore.cmdDisp.CommandsDispatched
    CdhCore.cmdDisp.CommandsDropped
    ComCcsds.comQueue.comQueueDepth
    ComCcsds.comQueue.buffQueueDepth
    ComCcsds.commsBufferManager.TotalBuffs
    ComCcsds.commsBufferManager.CurrBuffs
    ComCcsds.commsBufferManager.HiBuffs
    FprimeSoakTestReference.rateGroup1KHz.RgMaxTime
    FprimeSoakTestReference.rateGroup10Hz.RgMaxTime
    FprimeSoakTestReference.rateGroup1Hz.RgMaxTime
  }

  packet CDHErrors id 2 group 1 {
    CdhCore.$health.PingLateWarnings
    CdhCore.events.EventsDropped
    ComCcsds.commsBufferManager.NoBuffs
    ComCcsds.commsBufferManager.EmptyBuffs
    Rfm69.rfm69Manager.RxCrcErrors
    FprimeSoakTestReference.rateGroup1KHz.RgCycleSlips
    FprimeSoakTestReference.rateGroup10Hz.RgCycleSlips
    FprimeSoakTestReference.rateGroup1Hz.RgCycleSlips
  }

  # File / sequencer housekeeping — off default radio level (group 2+)
  packet FileSeq id 4 group 2 {
    FileHandling.fileUplink.FilesReceived
    FileHandling.fileUplink.PacketsReceived
    FileHandling.fileDownlink.FilesSent
    FileHandling.fileDownlink.PacketsSent
    FileHandling.fileManager.CommandsExecuted
    FprimeSoakTestReference.cmdSeq.CS_LoadCommands
    FprimeSoakTestReference.cmdSeq.CS_CancelCommands
    FprimeSoakTestReference.cmdSeq.CS_CommandsExecuted
    FprimeSoakTestReference.cmdSeq.CS_SequencesCompleted
    FileHandling.fileUplink.Warnings
    FileHandling.fileDownlink.Warnings
    FileHandling.fileManager.Errors
    FprimeSoakTestReference.cmdSeq.CS_Errors
  }

  packet SystemRes1 id 5 group 2 {
    FprimeSoakTestReference.systemResources.MEMORY_TOTAL
    FprimeSoakTestReference.systemResources.MEMORY_USED
    FprimeSoakTestReference.systemResources.NON_VOLATILE_TOTAL
    FprimeSoakTestReference.systemResources.NON_VOLATILE_FREE
  }

  packet SystemRes3 id 6 group 2 {
    FprimeSoakTestReference.systemResources.CPU
    FprimeSoakTestReference.systemResources.CPU_00
    FprimeSoakTestReference.systemResources.CPU_01
    FprimeSoakTestReference.systemResources.CPU_02
    FprimeSoakTestReference.systemResources.CPU_03
    FprimeSoakTestReference.systemResources.CPU_04
    FprimeSoakTestReference.systemResources.CPU_05
    FprimeSoakTestReference.systemResources.CPU_06
    FprimeSoakTestReference.systemResources.CPU_07
    FprimeSoakTestReference.systemResources.CPU_08
    FprimeSoakTestReference.systemResources.CPU_09
    FprimeSoakTestReference.systemResources.CPU_10
    FprimeSoakTestReference.systemResources.CPU_11
    FprimeSoakTestReference.systemResources.CPU_12
    FprimeSoakTestReference.systemResources.CPU_13
    FprimeSoakTestReference.systemResources.CPU_14
    FprimeSoakTestReference.systemResources.CPU_15
  }

  packet DataProducts id 21 group 3 {
    DataProducts.dpCat.CatalogDps
    DataProducts.dpCat.DpsSent

    DataProducts.dpMgr.NumSuccessfulAllocations
    DataProducts.dpMgr.NumFailedAllocations
    DataProducts.dpMgr.NumDataProducts
    DataProducts.dpMgr.NumBytes

    DataProducts.dpWriter.NumBuffersReceived
    DataProducts.dpWriter.NumBytesWritten
    DataProducts.dpWriter.NumSuccessfulWrites
    DataProducts.dpWriter.NumFailedWrites
    DataProducts.dpWriter.NumErrors

    DataProducts.dpBufferAccumulator.BA_NumQueuedBuffers

    DataProducts.dpBufferManager.TotalBuffs
    DataProducts.dpBufferManager.CurrBuffs
    DataProducts.dpBufferManager.HiBuffs
    DataProducts.dpBufferManager.NoBuffs
    DataProducts.dpBufferManager.EmptyBuffs
  }

  packet Version1 id 22 group 2 {
    CdhCore.version.FrameworkVersion
    CdhCore.version.ProjectVersion
  }

  packet Version_Library1 id 23 group 2 {
    CdhCore.version.LibraryVersion01
    CdhCore.version.LibraryVersion02
  }

  packet Version_Library2 id 24 group 2 {
    CdhCore.version.LibraryVersion03
    CdhCore.version.LibraryVersion04
  }

  packet Version_Library3 id 25 group 2 {
    CdhCore.version.LibraryVersion05
    CdhCore.version.LibraryVersion06
  }

  packet Version_Library4 id 26 group 2 {
    CdhCore.version.LibraryVersion07
    CdhCore.version.LibraryVersion08
  }

  packet Version_Library5 id 27 group 2 {
    CdhCore.version.LibraryVersion09
    CdhCore.version.LibraryVersion10
  }

  packet Version_Custom1 id 28 group 2 {
    CdhCore.version.CustomVersion01
  }

  packet Version_Custom2 id 29 group 2 {
    CdhCore.version.CustomVersion02
  }

  packet Version_Custom3 id 30 group 2 {
    CdhCore.version.CustomVersion03
  }

  packet Version_Custom4 id 31 group 2 {
    CdhCore.version.CustomVersion04
  }

  packet Version_Custom5 id 32 group 2 {
    CdhCore.version.CustomVersion05
  }

  packet Version_Custom6 id 33 group 2 {
    CdhCore.version.CustomVersion06
  }

  packet Version_Custom7 id 34 group 2 {
    CdhCore.version.CustomVersion07
  }

  packet Version_Custom8 id 35 group 2 {
    CdhCore.version.CustomVersion08
  }

  packet Version_Custom9 id 36 group 2 {
    CdhCore.version.CustomVersion09
  }

  packet Version_Custom10 id 37 group 2 {
    CdhCore.version.CustomVersion10
  }
  
  packet Sensor_Readings id 38 group 2  {
    Bmp280.bmpManager.Reading
    MpuImu.imuManager.Reading
  }

  packet Radio id 39 group 1 {
    Rfm69.rfm69Manager.PacketsTransmitted
    Rfm69.rfm69Manager.PacketsReceived
    Rfm69.rfm69Manager.LastRssi
    Rfm69.rfm69Manager.RadioState
  }

} omit {
  # Omit unused command dispatcher errors
  CdhCore.cmdDisp.CommandErrors

  # Omit TlmPacketizer internal telemetry
  CdhCore.tlmSend.GroupConfigs
  CdhCore.tlmSend.SectionEnabled

  # Omit low-level driver telemetry
  Bmp280.bmpDriver.SPI_Bytes
  Rfm69.spiDriver.SPI_Bytes

  #idk just build plz
  FprimeSoakTestReference.cmdSeq.CS_CurrentSequence
}
