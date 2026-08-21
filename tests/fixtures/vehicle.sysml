package Vehicle {
    doc /* Demonstration vehicle model. */
    part def Battery;
    part battery : Battery {
        attribute capacity = 75.0 [kWh];
        port dcBus;
    }
    part motor [2] {
        port dcIn;
    }
    connection powerFeed connect battery.dcBus to motor.dcIn;
    requirement <'REQ-001'> Range {
        doc /* The vehicle shall travel at least 400 km on one charge. */
    }
    requirement <'REQ-002'> BatteryMass {
        doc /* The battery shall weigh at most 500 kg. */
        subject battery;
    }
    dependency from BatteryMass to Range; // derive
    satisfy BatteryMass by battery;
    allocate Range to battery;
    analysis RangeAnalysis {
        subject battery;
        objective { doc /* Show the range requirement holds at nominal load. */ }
    }
    dependency from RangeAnalysis to Range; // verify
}
