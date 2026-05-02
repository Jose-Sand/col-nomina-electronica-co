"""
Módulo principal para cálculo de nómina colombiana y generación XML DIAN
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ConfiguracionDIAN(BaseModel):
    """Configuración para integración con DIAN"""
    certificado_path: Optional[str] = None
    password_certificado: Optional[str] = None
    prefijo_numeracion: str = "NOM"
    ambiente: str = Field(default="pruebas", pattern="^(pruebas|produccion)$")
    uvt_vigente: int = 47065  # UVT 2024
    salario_minimo: int = 1300000  # SMMLV 2024
    auxilio_transporte: int = 162000  # 2024


class Empleado(BaseModel):
    """Modelo de empleado con validaciones colombianas"""
    identificacion: str
    tipo_id: str = Field(pattern="^(CC|CE|NIT|PAS|PPT)$")
    nombres: str
    apellidos: str
    salario_mensual: int = Field(gt=0)
    cargo: str
    fecha_ingreso: date
    nivel_riesgo_arl: int = Field(ge=1, le=5)
    tipo_contrato: str = Field(default="INDEFINIDO")
    
    @validator("salario_mensual")
    def validar_salario(cls, v: int) -> int:
        if v < 1300000:  # Menor a SMMLV 2024
            raise ValueError("Salario no puede ser menor al SMMLV")
        return v


class Periodo(BaseModel):
    """Período de liquidación"""
    fecha_inicio: date
    fecha_fin: date
    fecha_pago: date
    dias_trabajados: int = 30
    
    @validator("dias_trabajados")
    def validar_dias(cls, v: int) -> int:
        if not 1 <= v <= 30:
            raise ValueError("Días trabajados debe estar entre 1 y 30")
        return v


@dataclass
class HoraExtra:
    """Hora extra con recargo legal"""
    tipo: str  # DIURNA=25%, NOCTURNA=75%, DOMINICAL=75%
    cantidad: int
    valor_hora: int


@dataclass
class Deduccion:
    """Deducción adicional de nómina"""
    concepto: str
    valor: int


@dataclass
class Liquidacion:
    """Resultado completo de liquidación de nómina"""
    empleado: Empleado
    periodo: Periodo
    salario_base: int
    horas_extras: int
    auxilio_transporte: int
    total_devengado: int
    salud_empleado: int
    pension_empleado: int
    retencion_fuente: int
    otras_deducciones: int
    total_deducciones: int
    cesantias: int
    intereses_cesantias: int
    prima: int
    vacaciones: int
    salud_empleador: int
    pension_empleador: int
    arl: int
    parafiscales: Dict[str, int]
    total_apropiaciones: int
    neto_pagar: int
    cune: str = ""


class NominaElectronica:
    """Calculadora y generador de nómina electrónica DIAN"""
    
    def __init__(
        self,
        numero_nomina: str,
        empleador_nit: str,
        empleador_razon_social: str,
        config: Optional[ConfiguracionDIAN] = None
    ):
        self.numero_nomina = numero_nomina
        self.empleador_nit = empleador_nit
        self.empleador_razon_social = empleador_razon_social
        self.config = config or ConfiguracionDIAN()
        
    def calcular_liquidacion(
        self,
        empleado: Empleado,
        periodo: Periodo,
        horas_extras: Optional[List[HoraExtra]] = None,
        deducciones_adicionales: Optional[List[Deduccion]] = None
    ) -> Liquidacion:
        """Calcula liquidación completa de nómina colombiana"""
        from .utils import (
            calcular_proporcional,
            calcular_arl_por_riesgo,
            calcular_retencion_fuente,
            calcular_cune
        )
        
        # Salario base proporcional a días trabajados
        salario_base = calcular_proporcional(
            empleado.salario_mensual, 
            periodo.dias_trabajados
        )
        
        # Horas extras
        valor_horas_extras = 0
        if horas_extras:
            valor_hora_ordinaria = empleado.salario_mensual / 240
            for he in horas_extras:
                recargo = {"DIURNA": 1.25, "NOCTURNA": 1.75, 
                          "DOMINICAL": 1.75}
                valor_horas_extras += int(
                    he.cantidad * valor_hora_ordinaria * recargo.get(he.tipo, 1.25)
                )
        
        # Auxilio de transporte (solo hasta 2 SMMLV)
        auxilio = 0
        if empleado.salario_mensual <= 2 * self.config.salario_minimo:
            auxilio = calcular_proporcional(
                self.config.auxilio_transporte,
                periodo.dias_trabajados
            )
        
        total_devengado = salario_base + valor_horas_extras + auxilio
        
        # Deducciones empleado
        salud_emp = int(total_devengado * 0.04)
        pension_emp = int(total_devengado * 0.04)
        
        # Retención en la fuente
        retencion = calcular_retencion_fuente(
            total_devengado,
            salud_emp + pension_emp,
            self.config.uvt_vigente
        )
        
        otras_deduc = sum(d.valor for d in deducciones_adicionales or [])
        total_deducciones = salud_emp + pension_emp + retencion + otras_deduc
        
        # Apropiaciones empleador
        cesantias = int(salario_base * 0.0833)
        intereses_ces = int(cesantias * 0.12 / 12)
        prima = int(salario_base * 0.0833)
        vacaciones = int(salario_base * 0.0417)
        
        salud_empl = int(total_devengado * 0.085)
        pension_empl = int(total_devengado * 0.12)
        arl = calcular_arl_por_riesgo(total_devengado, empleado.nivel_riesgo_arl)
        
        # Parafiscales (solo si gana > 10 SMMLV)
        parafiscales = {}
        if empleado.salario_mensual > 10 * self.config.salario_minimo:
            parafiscales = {
                "sena": int(total_devengado * 0.02),
                "icbf": int(total_devengado * 0.03),
                "caja": int(total_devengado * 0.04)
            }
        
        total_aprop = (cesantias + intereses_ces + prima + vacaciones + 
                      salud_empl + pension_empl + arl + sum(parafiscales.values()))
        
        neto = total_devengado - total_deducciones
        
        liquidacion = Liquidacion(
            empleado=empleado,
            periodo=periodo,
            salario_base=salario_base,
            horas_extras=valor_horas_extras,
            auxilio_transporte=auxilio,
            total_devengado=total_devengado,
            salud_empleado=salud_emp,
            pension_empleado=pension_emp,
            retencion_fuente=retencion,
            otras_deducciones=otras_deduc,
            total_deducciones=total_deducciones,
            cesantias=cesantias,
            intereses_cesantias=intereses_ces,
            prima=prima,
            vacaciones=vacaciones,
            salud_empleador=salud_empl,
            pension_empleador=pension_empl,
            arl=arl,
            parafiscales=parafiscales,
            total_apropiaciones=total_aprop,
            neto_pagar=neto
        )
        
        # Generar CUNE
        liquidacion.cune = calcular_cune(
            self.numero_nomina,
            self.empleador_nit,
            empleado.identificacion,
            periodo.fecha_pago.isoformat(),
            str(total_devengado),
            str(total_deducciones),
            str(neto)
        )
        
        return liquidacion
    
    def generar_xml_dian(self, liquidacion: Liquidacion) -> bytes:
        """Genera XML UBL 2.1 para nómina electrónica DIAN"""
        from lxml import etree
        
        NS = {
            None: "urn:dian:gov:co:facturaelectronica:NominaIndividual",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        }
        
        root = etree.Element("NominaIndividual", nsmap=NS)
        
        # Información básica
        ext = etree.SubElement(root, "{%s}UBLExtensions" % NS["ext"])
        cbc_version = etree.SubElement(root, "{%s}UBLVersionID" % NS["cbc"])
        cbc_version.text = "UBL 2.1"
        
        num = etree.SubElement(root, "{%s}ID" % NS["cbc"])
        num.text = self.numero_nomina
        
        cune_elem = etree.SubElement(root, "{%s}UUID" % NS["cbc"])
        cune_elem.text = liquidacion.cune
        
        fecha = etree.SubElement(root, "{%s}IssueDate" % NS["cbc"])
        fecha.text = liquidacion.periodo.fecha_pago.isoformat()
        
        # Devengados
        devengos = etree.SubElement(root, "Devengados")
        self._agregar_elemento(devengos, "Basico", str(liquidacion.salario_base))
        if liquidacion.horas_extras > 0:
            self._agregar_elemento(devengos, "HorasExtras", 
                                  str(liquidacion.horas_extras))
        
        # Deducciones
        deducciones = etree.SubElement(root, "Deducciones")
        self._agregar_elemento(deducciones, "Salud", 
                              str(liquidacion.salud_empleado))
        self._agregar_elemento(deducciones, "Pension", 
                              str(liquidacion.pension_empleado))
        
        # Total
        total = etree.SubElement(root, "Total")
        self._agregar_elemento(total, "DevengadosTotal", 
                              str(liquidacion.total_devengado))
        self._agregar_elemento(total, "DeduccionesTotal", 
                              str(liquidacion.total_deducciones))
        self._agregar_elemento(total, "ComprobanteTotal", 
                              str(liquidacion.neto_pagar))
        
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", 
                             pretty_print=True)
    
    def _agregar_elemento(self, parent: Any, tag: str, valor: str) -> None:
        """Helper para agregar elementos XML"""
        elem = etree.SubElement(parent, tag)
        elem.text = valor
