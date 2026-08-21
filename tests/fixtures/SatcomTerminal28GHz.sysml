package SatcomTerminal28GHz {
    public import RFVocabulary::*;
    public import RFParts::*;
    public import RFRequirements::*;
    public import RFAnalyses::*;
    doc /* 28 GHz LEO uplink phased-array ground terminal, mirroring the aedl t3-001 benchmark: close the worst-case link over the evaluation envelope inside a 450 W prime-power and 45 kUSD unit-cost ceiling. */
    part terminal : SatcomTerminal {
        part array : PhasedArrayAntenna {
            attribute frequency = 28.0 [GHz];
            attribute bandwidth = 50.0 [MHz];
            attribute maxScanAngle = 60.0 [deg];
            part elements : AntennaElement [1..*];
            part trModules : TRModule [1..*];
            part beamformer : Beamformer {
                port beamOut : BeamPort;
            }
        }
        part frontEnd : RFFrontEnd {
            port beamIn : BeamPort;
        }
        part modem : Modem;
        connection beamFeed connect array.beamformer.beamOut to frontEnd.beamIn;
    }
    requirement <'REQ-LINK-MARGIN'> WorstCaseLinkMargin {
        doc /* The link shall close (margin >= 0 dB) worst-case over the evaluation envelope. */
        attribute metricKey = "worst_case_link_margin_db";
        attribute threshold = 0.0 [dB];
        attribute op = ">=";
        attribute severity = "must";
    }
    requirement <'REQ-SLL'> PatternSidelobes {
        doc /* Worst-case pattern sidelobe level shall not exceed -16 dB. */
        attribute metricKey = "worst_case_pattern_sll_db";
        attribute threshold = -16.0 [dB];
        attribute op = "<=";
        attribute severity = "must";
    }
    requirement <'REQ-INDEP-LINK'> IndependentLinkClosure {
        doc /* The link shall also close under the independent opensatcom recomputation. */
        attribute metricKey = "opensatcom_worst_case_margin_db";
        attribute threshold = 0.0 [dB];
        attribute op = ">=";
        attribute severity = "must";
    }
    requirement <'REQ-CLEARSKY-AGREE'> ClearSkyAgreement {
        doc /* Clear-sky margins from the two link analyses shall agree within 1.2 dB. */
        attribute metricKey = "crosscheck_clearsky_margin_disagreement_db";
        attribute threshold = 1.2 [dB];
        attribute op = "<=";
        attribute severity = "should";
    }
    requirement <'REQ-GAIN-XCHECK'> GainCrosscheck {
        doc /* Claimed and integrated gain shall agree within 0.5 dB. */
        attribute metricKey = "crosscheck_gain_disagreement_db";
        attribute threshold = 0.5 [dB];
        attribute op = "<=";
        attribute severity = "should";
    }
    requirement <'REQ-POWER'> PrimePowerCeiling {
        doc /* Prime power draw shall not exceed 450 W. */
        attribute metricKey = "prime_power_w";
        attribute threshold = 450.0 [W];
        attribute op = "<=";
        attribute severity = "must";
    }
    requirement <'REQ-COST'> UnitCostCeiling {
        doc /* Recurring unit cost shall not exceed 45,000 USD from the parts table. */
        attribute metricKey = "unit_cost_usd";
        attribute threshold = 45000.0;
        attribute op = "<=";
        attribute severity = "must";
    }
    requirement <'REQ-GRATING'> GratingLobeMargin {
        doc /* The lattice shall keep grating lobes out of visible space over the scan envelope. */
        attribute metricKey = "grating_margin_lambda";
        attribute threshold = 0.0;
        attribute op = ">=";
        attribute severity = "must";
    }
    analysis linkBudget : LinkBudgetAnalysis {
        subject terminal;
        objective { doc /* Close the uplink worst-case over the t3-001 evaluation envelope. */ }
    }
    analysis patternAnalysis : ArrayPatternAnalysis {
        subject array;
        objective { doc /* Integrate the full pattern; recompute gain, sidelobes, grating margin. */ }
    }
    analysis swapCost : SwapCostAnalysis {
        subject terminal;
        objective { doc /* Roll up prime power and unit cost from the parts table. */ }
    }
    satisfy WorstCaseLinkMargin by terminal;
    satisfy IndependentLinkClosure by terminal;
    satisfy PatternSidelobes by terminal.array;
    satisfy GratingLobeMargin by terminal.array;
    satisfy PrimePowerCeiling by terminal;
    satisfy UnitCostCeiling by terminal;
    allocate PatternSidelobes to terminal.array;
    allocate GratingLobeMargin to terminal.array;
    allocate PrimePowerCeiling to terminal;
    dependency from linkBudget to WorstCaseLinkMargin; // verify
    dependency from linkBudget to IndependentLinkClosure; // verify
    dependency from linkBudget to ClearSkyAgreement; // verify
    dependency from patternAnalysis to PatternSidelobes; // verify
    dependency from patternAnalysis to GainCrosscheck; // verify
    dependency from patternAnalysis to GratingLobeMargin; // verify
    dependency from swapCost to PrimePowerCeiling; // verify
    dependency from swapCost to UnitCostCeiling; // verify
}
