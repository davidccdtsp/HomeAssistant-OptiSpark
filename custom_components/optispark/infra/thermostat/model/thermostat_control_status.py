from custom_components.optispark.infra.shared.model.base_enum import BaseEnum


class ThermostatControlStatus(str, BaseEnum):
    SCHEDULE = "schedule"
    MANUAL = "manual"
    BOOST = "boost"