package RFParts {
    doc /* Part and port definitions for phased-array antenna systems. */
    port def RFPort {
        doc /* Guided-wave RF interface. */
    }
    port def BeamPort {
        doc /* Formed-beam signal interface. */
    }
    port def CtrlPort {
        doc /* Command and telemetry interface. */
    }
    part def AntennaElement {
        doc /* A single radiating element. */
    }
    part def RadiatingAperture {
        doc /* The element lattice as one aperture. */
    }
    part def TRModule {
        doc /* Transmit/receive module: PA, LNA, phase shifter, switch. */
    }
    part def Beamformer {
        doc /* Analog, digital, or hybrid beamforming network. */
    }
    part def PhasedArrayAntenna {
        doc /* Aperture, T/R modules, and beamformer as one antenna. */
    }
    part def RFFrontEnd {
        doc /* Up/down conversion and filtering between antenna and modem. */
    }
    part def Modem {
        doc /* Waveform modulation and demodulation. */
    }
    part def SatcomTerminal {
        doc /* A complete ground terminal. */
    }
}
