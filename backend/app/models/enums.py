from enum import Enum


class UserRole(str, Enum):
    FARMER = "FARMER"
    COLD_STORE_OPERATOR = "COLD_STORE_OPERATOR"


class CommodityCode(str, Enum):
    POTATO = "POTATO"


class SupplyStatus(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    PARTIALLY_SOLD = "PARTIALLY_SOLD"
    SOLD = "SOLD"
    STORED = "STORED"
    CANCELLED = "CANCELLED"


class BuyerType(str, Enum):
    WHOLESALER = "WHOLESALER"
    RETAILER = "RETAILER"
    PROCESSOR = "PROCESSOR"
    RESTAURANT = "RESTAURANT"
    INSTITUTION = "INSTITUTION"
    OTHER = "OTHER"


class DemandStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FULFILLED = "FULFILLED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ColdStoreEventType(str, Enum):
    LOADING = "LOADING"
    RELEASE = "RELEASE"
    ADJUSTMENT = "ADJUSTMENT"
