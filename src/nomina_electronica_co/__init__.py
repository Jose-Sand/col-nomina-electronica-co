"""
Nómina Electrónica Colombia - Librería para cálculo y generación XML DIAN
"""
from .core import (
    NominaElectronica,
    Empleado,
    Periodo,
    Liquidacion,
    HoraExtra,
    Deduccion,
    ConfiguracionDIAN,
)
from .utils import calcular_cune, generar_numero_secuencial

__version__ = "1.0.0"
__all__ = [
    "NominaElectronica",
    "Empleado",
    "Periodo",
    "Liquidacion",
    "HoraExtra",
    "Deduccion",
    "ConfiguracionDIAN",
    "calcular_cune",
    "generar_numero_secuencial",
]
