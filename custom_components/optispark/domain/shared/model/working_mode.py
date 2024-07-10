from custom_components.optispark.domain.shared.model.base_enum import BaseEnum


class WorkingMode(str, BaseEnum):
    HEATING = "Heating"
    COOLING = "Cooling"
    STOPPED = "Stopped"
    HEAT_AND_COOL = "HeatAndCool"