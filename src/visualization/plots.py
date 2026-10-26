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
    save_path: Optional[str] = None
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
    ax.set_title(f'Utilizacion por etapa - c3={selected_c3} medicos, c5={selected_c5} enfermeros', fontsize=14)
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
    save_path: Optional[str] = None
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
    
    axes[5].axis('off')
    
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
    
    for bar, val in zip(bars1, fifo_means):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    for bar, val in zip(bars2, pri_means):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
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


def create_results_tables(
    analytical_results: List[Dict],
    validation_results: Dict[str, Any],
    priority_results: Dict[str, Any],
    output_dir: str = "output"
) -> Dict[str, pd.DataFrame]:
    os.makedirs(output_dir, exist_ok=True)
    
    tables = {}
    
    stage_names = ["Registro", "Triaje", "Consulta", "Laboratorio", "Tratamiento"]
    
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
    
    val_rows = []
    for label, val in validation_results.items():
        comp = val["comparison"]
        for stage_name, data in comp.items():
            if stage_name != "overall_passed":
                val_rows.append({
                    "Escenario": label,
                    "Etapa": stage_name,
                    "Wq_analitico (min)": round(data["analytical_Wq"] * 60, 2),
                    "Wq_simulacion (min)": round(data["simulation_Wq_mean"] * 60, 2),
                    "Diff_%": round(data["diff_pct"] * 100, 2),
                    "En_IC95": "Sí" if data["in_ci"] else "No",
                    "Validación": "PASA" if data["passed"] else "FALLA"
                })
    
    tables["validation"] = pd.DataFrame(val_rows)
    tables["validation"].to_csv(f"{output_dir}/tabla_validacion.csv", index=False)
    
    pri_rows = []
    for label, pri in priority_results.items():
        for g_name, comp in pri["gravity_comparison"].items():
            pri_rows.append({
                "Escenario": label,
                "Gravedad": g_name,
                "Wq_sin_prioridad (min)": round(comp["fifo_Wq"] * 60, 2),
                "Wq_con_prioridad (min)": round(comp["priority_Wq"] * 60, 2),
                "Diferencia (min)": round(comp["difference"] * 60, 2),
                "Mejora_%": round(comp["improvement_pct"], 1)
            })
    
    tables["priority_comparison"] = pd.DataFrame(pri_rows)
    tables["priority_comparison"].to_csv(f"{output_dir}/tabla_prioridad.csv", index=False)
    
    print(f"\nTablas guardadas en {output_dir}/")
    for name, df in tables.items():
        print(f"  - {name}: {len(df)} filas")
    
    return tables