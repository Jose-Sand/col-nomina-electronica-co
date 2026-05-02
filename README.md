# Nómina Electrónica Colombia

Librería Python para automatizar el cálculo completo de nómina colombiana y generar XML UBL 2.1 firmado para nómina electrónica DIAN con CUNE SHA-384.

## Características

- ✅ Cálculo automático de prestaciones sociales (cesantías 8.33%, prima, vacaciones, intereses cesantías 12% anual)
- ✅ Aportes seguridad social PILA: salud (12.5% total), pensión (16% total), ARL según riesgo
- ✅ Retención en la fuente sobre salarios según tabla UVT DIAN 2024
- ✅ Generación XML UBL 2.1 para nómina electrónica DIAN
- ✅ CUNE (Código Único Nómina Electrónica) con SHA-384
- ✅ Validación de aportes parafiscales según salario

## Instalación

```bash
pip install nomina-electronica-co
```

## Uso Rápido

```python
from nomina_electronica_co import NominaElectronica, Empleado, Periodo
from datetime import date

# Configurar empleado
empleado = Empleado(
    identificacion="1234567890",
    tipo_id="CC",
    nombres="Juan",
    apellidos="Pérez García",
    salario_mensual=3500000,
    cargo="Desarrollador Senior",
    fecha_ingreso=date(2023, 1, 15),
    nivel_riesgo_arl=1  # 0.522% para riesgo I
)

# Configurar período de pago
periodo = Periodo(
    fecha_inicio=date(2024, 1, 1),
    fecha_fin=date(2024, 1, 31),
    fecha_pago=date(2024, 2, 5)
)

# Calcular nómina
nomina = NominaElectronica(
    numero_nomina="NOM-2024-001",
    empleador_nit="900123456",
    empleador_razon_social="Tech Solutions SAS"
)

liquidacion = nomina.calcular_liquidacion(empleado, periodo)

print(f"Salario base: ${liquidacion.salario_base:,.0f}")
print(f"Devengado total: ${liquidacion.total_devengado:,.0f}")
print(f"Deducciones: ${liquidacion.total_deducciones:,.0f}")
print(f"Neto a pagar: ${liquidacion.neto_pagar:,.0f}")

# Generar XML UBL 2.1 firmado
xml_firmado = nomina.generar_xml_dian(liquidacion)
print(f"CUNE: {liquidacion.cune}")
```

## Cálculos Soportados

### Prestaciones Sociales
- **Cesantías**: 8.33% mensual (salario × días trabajados / 360)
- **Prima de servicios**: 8.33% mensual (salario × días / 360)
- **Vacaciones**: 4.17% mensual (15 días hábiles por año)
- **Intereses cesantías**: 12% anual sobre cesantías acumuladas

### Seguridad Social (PILA)
- **Salud**: 12.5% (empleado 4%, empleador 8.5%)
- **Pensión**: 16% (empleado 4%, empleador 12%)
- **ARL**: 0.522% a 6.96% según nivel de riesgo (100% empleador)

### Parafiscales (> 10 SMMLV)
- **SENA**: 2% del salario
- **ICBF**: 3% del salario
- **Caja compensación**: 4% del salario

### Retención en la Fuente
Según tabla UVT DIAN 2024 con deducciones permitidas:
- Aportes obligatorios salud y pensión
- Intereses vivienda
- Medicina prepagada (límite)
- Dependientes

## Ejemplo Completo

```python
from nomina_electronica_co import (
    NominaElectronica, Empleado, Periodo, 
    Deduccion, HoraExtra
)
from datetime import date

empleado = Empleado(
    identificacion="1234567890",
    tipo_id="CC",
    nombres="María",
    apellidos="López Ramírez",
    salario_mensual=5000000,
    cargo="Gerente de Proyectos",
    fecha_ingreso=date(2020, 3, 1),
    nivel_riesgo_arl=2,  # 1.044% riesgo II
    tipo_contrato="INDEFINIDO"
)

periodo = Periodo(
    fecha_inicio=date(2024, 1, 1),
    fecha_fin=date(2024, 1, 31),
    fecha_pago=date(2024, 2, 5),
    dias_trabajados=30
)

# Agregar horas extras
horas_extras = [
    HoraExtra(tipo="DIURNA", cantidad=10, valor_hora=20833),
    HoraExtra(tipo="NOCTURNA", cantidad=5, valor_hora=29167)
]

# Agregar deducciones adicionales
deducciones = [
    Deduccion(concepto="LIBRANZA", valor=200000),
    Deduccion(concepto="FONDO_EMPLEADOS", valor=100000)
]

nomina = NominaElectronica(
    numero_nomina="NOM-2024-001",
    empleador_nit="900123456",
    empleador_razon_social="Tech Solutions SAS",
    ambiente="produccion"  # "pruebas" o "produccion"
)

liquidacion = nomina.calcular_liquidacion(
    empleado, 
    periodo,
    horas_extras=horas_extras,
    deducciones_adicionales=deducciones
)

# Exportar XML para DIAN
xml_bytes = nomina.generar_xml_dian(liquidacion)
with open("nomina_electronica.xml", "wb") as f:
    f.write(xml_bytes)

# Generar reporte PDF (opcional)
pdf_bytes = nomina.generar_desprendible_pdf(liquidacion)
```

## Estructura de Liquidación

```python
{
    "empleado": {...},
    "periodo": {...},
    "devengos": {
        "salario_base": 5000000,
        "horas_extras": 354165,
        "auxilio_transporte": 0,  # Solo si gana <= 2 SMMLV
        "total": 5354165
    },
    "deducciones": {
        "salud": 200000,  # 4% empleado
        "pension": 200000,  # 4% empleado
        "retencion_fuente": 385000,
        "otras": 300000,
        "total": 1085000
    },
    "apropiaciones": {
        "cesantias": 445347,
        "intereses_cesantias": 53442,
        "prima": 445347,
        "vacaciones": 222673,
        "salud_empleador": 425000,  # 8.5%
        "pension_empleador": 600000,  # 12%
        "arl": 52200,  # 1.044% riesgo II
        "total": 2244009
    },
    "total_devengado": 5354165,
    "total_deducciones": 1085000,
    "neto_pagar": 4269165,
    "cune": "a1b2c3..."
}
```

## Cumplimiento DIAN

- ✅ XML UBL 2.1 namespace: `urn:dian:gov:co:facturaelectronica:NominaIndividual`
- ✅ CUNE con algoritmo SHA-384
- ✅ Numeración consecutiva autorizada
- ✅ Validación previa con servicio DIAN (opcional)
- ✅ Campos obligatorios según resolución 000013 de 2021

## Configuración Avanzada

```python
from nomina_electronica_co import ConfiguracionDIAN

config = ConfiguracionDIAN(
    certificado_path="/path/to/certificado.p12",
    password_certificado="password",
    prefijo_numeracion="NOM",
    ambiente="produccion",
    uvt_vigente=47065,  # UVT 2024
    salario_minimo=1300000  # SMMLV 2024
)

nomina = NominaElectronica(
    numero_nomina="NOM-2024-001",
    empleador_nit="900123456",
    empleador_razon_social="Tech Solutions SAS",
    config=config
)
```

## Requisitos

- Python >= 3.9
- lxml >= 4.9.0
- cryptography >= 41.0.0
- pydantic >= 2.0.0

## Licencia

MIT License - Ver archivo LICENSE

## Soporte

Para reportar errores o solicitar características: https://github.com/tu-usuario/nomina-electronica-co/issues

## Contribuir

Las contribuciones son bienvenidas. Por favor, abre un issue primero para discutir cambios mayores.

---
Desarrollado con ❤️ para el ecosistema de nómina electrónica en Colombia
