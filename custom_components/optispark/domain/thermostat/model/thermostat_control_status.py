from custom_components.optispark.domain.shared.model.base_enum import BaseEnum


class ThermostatControlStatus(str, BaseEnum):
    SCHEDULE = "schedule"
    MANUAL = "manual"
    BOOST = "boost"