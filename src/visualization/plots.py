import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import os


def plot_utilization_by_stage(
    analytical_results: List[Dict],
    selected_c3: int,
    selected_c5: int,
    save_path: Optional[str] = None,
    scenario_label: Optional[str] = None
):
    target = None
    for r in analytical_results:
        if r["c3"] == selected_c3 and r["c5"] == selected_c5:
            target = r
            break

    if target is None:
        print(f"No se encontró resultado para c3={selected_c3}, c5={selected_c5}")
        return

    stages = [s["name"] for s in target["stages"]]
    rhos = [s["rho"] for s in target["stages"]]
    colors = ['red' if s["is_bottleneck"] else 'steelblue' for s in target["stages"]]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(stages, rhos, color=colors, edgecolor='black', alpha=0.8)
    ax.axhline(y=1.0, color='red', linestyle='--', linewidth=1, label='Límite estabilidad (ρ=1)')
    ax.axhline(y=0.85, color='orange', linestyle=':', linewidth=1, label='Umbral recomendado (ρ=0.85)')

    for bar, rho in zip(bars, rhos):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{rho:.3f}', ha='center', va='bottom', fontweight='bold')

    ax.set_ylabel('Utilización (ρ)', fontsize=12)
    if scenario_label:
        ax.set_title(f'Utilización por etapa - Escenario {scenario_label} '
                     f'(c3={selected_c3} médicos, c5={selected_c5} enfermeros)', fontsize=14)
    else:
        ax.set_title(f'Utilización por etapa - c3={selected_c3} medicos, c5={selected_c5} enfermeros', fontsize=14)
    ax.set_ylim(0, max(1.1, max(rhos) * 1.2))
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_wait_vs_doctors(
    analytical_results: List[Dict],
    fixed_c5: int,
    save_path: Optional[str] = None,
    scenario_label: Optional[str] = None,
    highlight_c3: Optional[int] = None
):
    filtered = [r for r in analytical_results if r["c5"] == fixed_c5 and r["is_stable"]]
    if not filtered:
        print(f"No hay resultados estables para c5={fixed_c5}")
        return

    filtered.sort(key=lambda x: x["c3"])
    c3_vals = [r["c3"] for r in filtered]

    stage_names = ["Registro", "Triaje", "Consulta", "Laboratorio", "Tratamiento"]
    stage_indices = {name: i for i, name in enumerate(stage_names)}

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    for idx, stage_name in enumerate(stage_names):
        ax = axes[idx]
        Wq_vals = [r["stages"][stage_indices[stage_name]]["Wq"] * 60 for r in filtered]

        ax.plot(c3_vals, Wq_vals, 'o-', linewidth=2, markersize=8, color='steelblue')
        ax.set_xlabel('Medicos (c3)', fontsize=11)
        ax.set_ylabel('Espera en cola Wq (min)', fontsize=11)
        ax.set_title(f'{stage_name}', fontsize=12)
        ax.grid(True, alpha=0.3)

        for x, y in zip(c3_vals, Wq_vals):
            ax.annotate(f'{y:.1f}', (x, y), textcoords="offset points",
                       xytext=(0, 5), ha='center', fontsize=9)

        # Resalta el punto correspondiente a la configuración del escenario
        if highlight_c3 is not None and highlight_c3 in c3_vals:
            hi_y = [y for xv, y in zip(c3_vals, Wq_vals) if xv == highlight_c3][0]
            ax.plot([highlight_c3], [hi_y], 'o', markersize=13, color='crimson',
                    markeredgecolor='black', zorder=5)

    axes[5].axis('off')

    if scenario_label:
        fig.suptitle(f'Escenario {scenario_label}: espera en cola por etapa vs. '
                     f'número de médicos (c5={fixed_c5} enfermeros fijos)', fontsize=14)
    else:
        fig.suptitle(f'Espera en cola por etapa vs. Numero de medicos (c5={fixed_c5} enfermeros fijos)', fontsize=14)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_wait_by_gravity(
    priority_results: Dict[str, Any],
    scenario_label: str,
    save_path: Optional[str] = None
):
    gravity_order = ["CRITICAL", "URGENT", "MODERATE", "MILD", "NON_URGENT"]
    gravity_labels = ["Crítico (1)", "Urgente (2)", "Moderado (3)", "Leve (4)", "No urgente (5)"]

    fifo_means = []
    pri_means = []
    fifo_cis = []
    pri_cis = []

    for g in gravity_order:
        if g in priority_results["fifo"]["gravity_means"]:
            fifo_means.append(priority_results["fifo"]["gravity_means"][g]["Wq"] * 60)
            fifo_cis.append(priority_results["fifo"]["gravity_ci95"][g]["Wq"])
        else:
            fifo_means.append(0)
            fifo_cis.append((0, 0))

        if g in priority_results["priority"]["gravity_means"]:
            pri_means.append(priority_results["priority"]["gravity_means"][g]["Wq"] * 60)
            pri_cis.append(priority_results["priority"]["gravity_ci95"][g]["Wq"])
        else:
            pri_means.append(0)
            pri_cis.append((0, 0))

    fifo_cis = np.array(fifo_cis).T
    pri_cis = np.array(pri_cis).T

    # Ensure error bars are non-negative
    fifo_err_lower = np.maximum(0, fifo_means - fifo_cis[0])
    fifo_err_upper = np.maximum(0, fifo_cis[1] - fifo_means)
    pri_err_lower = np.maximum(0, pri_means - pri_cis[0])
    pri_err_upper = np.maximum(0, pri_cis[1] - pri_means)

    x = np.arange(len(gravity_labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 7))

    bars1 = ax.bar(x - width/2, fifo_means, width, label='Sin prioridad (FIFO)',
                   color='lightcoral', edgecolor='black', alpha=0.8,
                   yerr=[fifo_err_lower, fifo_err_upper], capsize=5)
    bars2 = ax.bar(x + width/2, pri_means, width, label='Con prioridad (gravedad)',
                   color='mediumseagreen', edgecolor='black', alpha=0.8,
                   yerr=[pri_err_lower, pri_err_upper], capsize=5)

    # Desplazamiento de etiquetas proporcional a la escala de la grafica
    max_val = max(fifo_means + pri_means + [1.0])
    label_offset = 0.03 * max_val

    for bar, val in zip(bars1, fifo_means):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + label_offset,
                    f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    for bar, val in zip(bars2, pri_means):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + label_offset,
                    f'{val:.1f}', ha='center', va='bottom', fontsize=9)

    ax.set_ylabel('Tiempo medio de espera en cola (min)', fontsize=12)
    ax.set_xlabel('Nivel de gravedad', fontsize=12)
    ax.set_title(f'Espera por gravedad: con vs. sin prioridad - {scenario_label}', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(gravity_labels)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


# ============================================================================
# Utilidades de tolerancia para los CSV
# ============================================================================

def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _first_num(data: Dict, keys, scale: float = 1.0) -> Optional[float]:
    """Devuelve el primer valor numerico encontrado en data para las claves
    dadas (multiplicado por scale), o None si no hay ninguno."""
    for k in keys:
        v = data.get(k)
        if _is_num(v):
            return v * scale
    return None


def create_results_tables(
    analytical_results: List[Dict],
    validation_results: Dict[str, Any],
    priority_results: Dict[str, Any],
    output_dir: str = "output"
) -> Dict[str, pd.DataFrame]:
    """Guarda las 4 tablas de resultados en CSV.

    TOLERANTE: 'comparison' (validacion) puede traer claves extra escalares
    ademas de las 5 etapas (p.ej. overall_passed, abs_tol_min). Esas claves
    NO son etapas: se ignoran. Antes, una clave escalar como abs_tol_min
    (un float) llegaba a data["analytical_Wq"] y provocaba el error
    TypeError: 'float' object is not subscriptable.

    Ademas, cada tabla esta protegida con su propio try/except: si una
    estructura no es la esperada, se avisa en consola pero la corrida
    NUNCA se detiene en la etapa de reportes.
    """
    os.makedirs(output_dir, exist_ok=True)

    tables = {}

    # ------------------------------------------------------------------
    # TABLA 1 (CSV): detalle analitico por etapa del barrido completo
    # ------------------------------------------------------------------
    try:
        rows = []
        for r in analytical_results:
            if r["is_stable"]:
                for s in r["stages"]:
                    rows.append({
                        "c3": r["c3"],
                        "c5": r["c5"],
                        "Etapa": s["name"],
                        "λ_eff (pac/h)": round(s["lambda_eff"], 2),
                        "μ (pac/h)": s["mu"],
                        "c": s["c"],
                        "ρ": round(s["rho"], 4),
                        "Wq (min)": round(s["Wq"] * 60, 2),
                        "W (min)": round(s["W"] * 60, 2),
                        "Lq": round(s["Lq"], 2),
                        "L": round(s["L"], 2),
                        "Cuello botella": "Sí" if s["is_bottleneck"] else "No"
                    })

        tables["analytical_detail"] = pd.DataFrame(rows)
        tables["analytical_detail"].to_csv(f"{output_dir}/tabla_analitico_detalle.csv", index=False)
    except Exception as e:
        print(f"  [aviso] No se pudo guardar tabla_analitico_detalle.csv: "
              f"{type(e).__name__}: {e}")

    # ------------------------------------------------------------------
    # TABLA 2 (CSV): resumen del barrido analitico
    # ------------------------------------------------------------------
    try:
        summary_rows = []
        for r in analytical_results:
            if r["is_stable"]:
                bn = r["stages"][r["bottleneck_idx"]]["name"] if r["bottleneck_idx"] >= 0 else "N/A"
                summary_rows.append({
                    "c3": r["c3"],
                    "c5": r["c5"],
                    "Estable": "Sí",
                    "Cuello de botella": bn,
                    "ρ_max": round(max(s["rho"] for s in r["stages"]), 4),
                    "W_sistema (min)": round(r["W_system"] * 60, 2),
                    "L_total": round(r["total_L"], 2)
                })
            else:
                summary_rows.append({
                    "c3": r["c3"],
                    "c5": r["c5"],
                    "Estable": "No",
                    "Cuello de botella": "Inestable",
                    "ρ_max": round(max(s["rho"] for s in r["stages"]), 4),
                    "W_sistema (min)": "∞",
                    "L_total": "∞"
                })

        tables["analytical_summary"] = pd.DataFrame(summary_rows)
        tables["analytical_summary"].to_csv(f"{output_dir}/tabla_analitico_resumen.csv", index=False)
    except Exception as e:
        print(f"  [aviso] No se pudo guardar tabla_analitico_resumen.csv: "
              f"{type(e).__name__}: {e}")

    # ------------------------------------------------------------------
    # TABLA 3 (CSV): validacion analitico vs simulacion
    # Solo se procesan las etapas (valores dict con campos de la etapa).
    # ------------------------------------------------------------------
    try:
        val_rows = []
        for label, val in validation_results.items():
            if not isinstance(val, dict):
                continue
            comp = val.get("comparison", {})
            if not isinstance(comp, dict):
                continue

            for stage_name, data in comp.items():
                if stage_name == "overall_passed":
                    continue
                # Solo etapas: el valor debe ser un dict. Escalares como
                # abs_tol_min (float) se ignoran y no rompen la corrida.
                if not isinstance(data, dict):
                    continue

                wq_an = _first_num(data, ("analytical_Wq", "Wq_analitico", "analytical"))
                if wq_an is None:
                    continue
                wq_sim = _first_num(data, ("simulation_Wq_mean", "Wq_simulacion", "simulation"))
                diff = _first_num(data, ("diff_pct", "diff", "difference"))
                in_ci = data.get("in_ci")
                passed = data.get("passed")

                abs_diff_min = data.get("abs_diff_min")
                if not _is_num(abs_diff_min):
                    abs_diff_min = abs(wq_an - wq_sim) * 60 if wq_sim is not None else None

                val_rows.append({
                    "Escenario": label,
                    "Etapa": stage_name,
                    "Wq_analitico (min)": round(wq_an * 60, 2),
                    "Wq_simulacion (min)": round(wq_sim * 60, 2) if wq_sim is not None else "-",
                    "Diff_%": round(diff * 100, 2) if diff is not None else "-",
                    "Diff_abs (min)": round(abs_diff_min, 3) if abs_diff_min is not None else "-",
                    "En_IC95": "Sí" if in_ci else ("No" if in_ci is not None else "-"),
                    "Validación": "PASA" if passed else ("FALLA" if passed is not None else "-")
                })

        tables["validation"] = pd.DataFrame(val_rows)
        tables["validation"].to_csv(f"{output_dir}/tabla_validacion.csv", index=False)
    except Exception as e:
        print(f"  [aviso] No se pudo guardar tabla_validacion.csv: "
              f"{type(e).__name__}: {e}")

    # ------------------------------------------------------------------
    # TABLA 4 (CSV): comparacion FIFO vs prioridad por gravedad
    # ------------------------------------------------------------------
    try:
        pri_rows = []
        for label, pri in priority_results.items():
            if not isinstance(pri, dict):
                continue
            gc = pri.get("gravity_comparison", {})
            if not isinstance(gc, dict):
                gc = {}

            for g_name, comp in gc.items():
                if not isinstance(comp, dict):
                    continue
                fifo_wq = comp.get("fifo_Wq")
                pri_wq = comp.get("priority_Wq")
                if not _is_num(fifo_wq) or not _is_num(pri_wq):
                    continue

                diff = comp.get("difference")
                if not _is_num(diff):
                    diff = pri_wq - fifo_wq
                imp = comp.get("improvement_pct")
                if not _is_num(imp):
                    imp = ((fifo_wq - pri_wq) / fifo_wq * 100) if fifo_wq > 0 else 0.0

                pri_rows.append({
                    "Escenario": label,
                    "Gravedad": g_name,
                    "Wq_sin_prioridad (min)": round(fifo_wq * 60, 2),
                    "Wq_con_prioridad (min)": round(pri_wq * 60, 2),
                    "Diferencia (min)": round(diff * 60, 2),
                    "Mejora_%": round(imp, 1)
                })

        tables["priority_comparison"] = pd.DataFrame(pri_rows)
        tables["priority_comparison"].to_csv(f"{output_dir}/tabla_prioridad.csv", index=False)
    except Exception as e:
        print(f"  [aviso] No se pudo guardar tabla_prioridad.csv: "
              f"{type(e).__name__}: {e}")

    print(f"\nTablas guardadas en {output_dir}/")
    for name, df in tables.items():
        print(f"  - {name}: {len(df)} filas")

    return tables
