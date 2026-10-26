# Modelado de Servicio de Emergencias - Redes de Colas de Jackson

Implementación de un modelo analítico (red de Jackson + Erlang C) y simulación de eventos discretos (SimPy) para optimización de personal en urgencias hospitalarias.

## Estructura del Proyecto

```
src/
├── config/          # Configuración y validación (YAML + Pydantic)
├── models/          # Modelo analítico y entidades
│   ├── analytical.py    # Red de Jackson + Erlang C
│   └── entities.py      # Patient, StageConfig, SimulationMetrics
├── simulation/      # Simulación SimPy con Strategy Pattern
│   ├── engine.py           # Motor de simulación principal
│   ├── priority_strategy.py # FIFO / Prioridad no expropiativa
│   ├── patient_generator.py # Generador de llegadas Poisson
│   └── statistics.py       # Agregación + IC95% + Validación
├── experiments/     # Experimentos y barridos
│   ├── runner.py    # Ejecución de réplicas
│   └── sweep.py     # Barrido c3×c5 + búsqueda mínimo
├── visualization/   # Gráficas y tablas
│   └── plots.py     # 3 gráficas requeridas + CSV
└── main.py          # Punto de entrada
```

## Instalación

```bash
pip install -r requirements.txt
```

## Configuración

Editar `config/base_parameters.yaml`:

- **external_arrivals.gamma**: Llegadas externas por hora (solo registro)
- **service_rates.mu**: Tasas de servicio por servidor/hora
- **servers.c**: Servidores por etapa (c₃=médicos, c₅=enfermeros)
- **routing_matrix.p**: Matriz de enrutamiento 5×5
- **gravity_levels.distribution**: % pacientes por gravedad (5 niveles)
- **simulation**: Réplicas, horizonte, warm-up, seed, umbral validación
- **parameter_sweep**: Rangos c₃/c₅ y escenarios seleccionados

## Ejecución

```bash
python -m src.main
```

Genera en `output/`:
- `grafica_utilizacion.png` - Utilización por etapa (cuello de botella en rojo)
- `grafica_espera_vs_medicos.png` - Wq por etapa vs c₃ (c₅ fijo)
- `grafica_espera_gravedad.png` - Espera por gravedad con/sin prioridad
- `tabla_analitico_detalle.csv` - Resultados analíticos completos
- `tabla_analitico_resumen.csv` - Resumen por configuración
- `tabla_validacion.csv` - Analítico vs Simulación (diff% + IC95%)
- `tabla_prioridad.csv` - Comparación FIFO vs Prioridad por gravedad

## Tests

```bash
pytest tests/ -v
```

## Modelo Analítico

**Red de Jackson abierta** con 5 etapas y realimentación:
1. Ecuaciones de tráfico: λ = (I - Pᵀ)⁻¹ γ
2. Cada etapa: M/M/c con Erlang C
3. Métricas: ρ, Wq, W, Lq, L (Ley de Little)
4. Cuello de botella = etapa con max ρ

## Simulación

**SimPy** - Eventos discretos con dos modos:
- **FIFO**: Validación vs modelo analítico
- **Prioridad no expropiativa**: Desde triaje, atiende más grave primero
- 30 réplicas, 1000h, warm-up 100h, seeds fijas
- IC95% para todas las métricas

## Patrones de Diseño

- **Strategy**: Modos de prioridad (FIFO / Priority)
- **Factory**: Creación de pacientes y estrategias
- **Builder**: Configuración de experimentos
- **Observer**: Recolección de métricas durante simulación
- **Template Method**: Flujo de procesamiento de paciente
- **Dependency Injection**: Configuración externa YAML