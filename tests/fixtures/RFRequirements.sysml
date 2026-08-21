package RFRequirements {
    doc /* Requirement definitions for RF terminals. Usages own attributes metricKey (str), threshold (number with unit), op (>=, <=, ==), and optionally severity (must/should/nice); sysml2kit.interop reads them. */
    requirement def EirpRequirement {
        doc /* Minimum effective isotropic radiated power. */
    }
    requirement def GOverTRequirement {
        doc /* Minimum receive figure of merit. */
    }
    requirement def SidelobeRequirement {
        doc /* Maximum pattern sidelobe level. */
    }
    requirement def ScanLossRequirement {
        doc /* Maximum gain loss at the scan-angle extreme. */
    }
    requirement def LinkMarginRequirement {
        doc /* Minimum worst-case link margin. */
    }
    requirement def BandwidthRequirement {
        doc /* Minimum instantaneous bandwidth. */
    }
    requirement def PowerCeilingRequirement {
        doc /* Maximum prime-power draw. */
    }
    requirement def CostCeilingRequirement {
        doc /* Maximum recurring unit cost. */
    }
    requirement def CrosscheckRequirement {
        doc /* Maximum disagreement between independent analyses. */
    }
    requirement def GratingLobeRequirement {
        doc /* Minimum grating-lobe margin in wavelengths. */
    }
}
