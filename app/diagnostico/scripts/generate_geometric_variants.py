import sys

import matplotlib.patches as patches
import matplotlib.pyplot as plt


def draw_square_figure(num_squares, output_path):
    """
    Genera una figura compuesta de cuadrados congruentes.
    Q45 original: 10 cuadrados.
    Variantes: 8, 12, etc.
    """
    fig, ax = plt.subplots(figsize=(6, 6))

    # Configuración base: L shape o similar para asegurar conectividad
    # Coordenadas (x, y) de cada cuadrado unitario
    if num_squares == 8:
        squares = [(0,0), (1,0), (2,0), (3,0),
                   (0,1), (1,1),
                   (0,2), (1,2)]
    elif num_squares == 10: # Original-like
        squares = [(0,0), (1,0), (2,0),
                   (0,1), (1,1), (2,1),
                   (0,2), (1,2),
                   (0,3), (1,3)]
    elif num_squares == 12:
        squares = [(0,0), (1,0), (2,0), (3,0),
                   (0,1), (1,1), (2,1), (3,1),
                   (1,2), (2,2),
                   (1,3), (2,3)]
    else:
        # Fallback simple vertical stack
        squares = [(0, i) for i in range(num_squares)]

    for x, y in squares:
        # Dibujar cuadrado contorno negro, relleno gris claro
        rect = patches.Rectangle((x, y), 1, 1, linewidth=2, edgecolor='black', facecolor='#e0e0e0')
        ax.add_patch(rect)

    ax.set_xlim(-1, 5)
    ax.set_ylim(-1, 5)
    ax.set_aspect('equal')
    ax.axis('off')

    plt.savefig(output_path, bbox_inches='tight', dpi=100)
    plt.close()
    print(f"Generated {output_path}")

def draw_boxplot(stats, output_path, xlabel=""):
    """
    Genera un diagrama de cajón (boxplot) estilo PAES exacto.
    stats = [min, q1, med, q3, max]
    """
    fig, ax = plt.subplots(figsize=(8, 3))

    # Configuración de estilo
    box_props = dict(facecolor='white', edgecolor='black', linewidth=1.2)
    median_props = dict(color='black', linewidth=1.2)
    whisker_props = dict(color='black', linewidth=1.2)
    cap_props = dict(color='black', linewidth=1.2)

    # Datos para boxplot
    item = {
        'label': '',
        'whislo': stats[0],
        'q1': stats[1],
        'med': stats[2],
        'q3': stats[3],
        'whishi': stats[4],
        'fliers': []
    }

    # Dibujar boxplot
    ax.bxp([item], vert=False, patch_artist=True,
                boxprops=box_props,
                medianprops=median_props,
                whiskerprops=whisker_props,
                capprops=cap_props,
                widths=0.5, # Ancho de la caja
                positions=[1])

    # Líneas punteadas verticales
    # Desde el eje X (y=0.5 aprox si usamos ylim 0.5-1.5) hasta la característica
    ylim_bottom = 0.5
    for x in stats:
        ax.vlines(x=x, ymin=ylim_bottom, ymax=1.0, # Hasta el centro/caja
                  colors='black', linestyles='dashed', linewidth=1)

    # Configuración de Ejes
    ax.set_ylim(0.5, 1.5)
    ax.set_xlim(stats[0]*0.9, stats[4]*1.1)

    # Eje X
    ax.spines['bottom'].set_position(('data', ylim_bottom))
    ax.spines['bottom'].set_linewidth(1.2)
    ax.set_xticks(stats)
    ax.set_xticklabels([f"{int(x)}" for x in stats], fontsize=11)
    ax.set_xlabel(xlabel, fontsize=12, labelpad=10)

    # Ocultar otros ejes
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.get_yaxis().set_visible(False)

    plt.savefig(output_path, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Generated {output_path}")

def draw_cylinders(output_path, h_val=10, r1_val=6, r2_val=8):
    """
    Genera una representación esquemática de 2 cilindros apilados con COTAS.
    h_val: Altura de cada cilindro
    r1_val: Radio superior
    r2_val: Radio inferior
    """
    fig, ax = plt.subplots(figsize=(6, 6))

    # Escalar dimensiones para dibujo (mantener proporciones visuales agradables)
    # Base width fija ~4 unidades. R2=8 -> width=4. R1=6 -> width=3
    scale_r = 4.0 / r2_val
    r2_draw = r2_val * scale_r / 2 # radio visual
    r1_draw = r1_val * scale_r / 2

    # Coordenadas
    # Cilindro abajo: Centro (2, 2) (mitad altura)
    # y range: 1 a 3
    y_base = 1
    y_mid = 3
    y_top = 5
    x_center = 4 # Más espacio a la izquierda para cotas

    # Elipses y cuerpos
    # Abajo
    # Elipse base
    ax.add_patch(patches.Ellipse((x_center, y_base), r2_draw*2, 0.6, edgecolor='black', facecolor='#e0e0e0', zorder=1))
    # Cuerpo
    ax.add_patch(patches.Rectangle((x_center-r2_draw, y_base), r2_draw*2, (y_mid-y_base), edgecolor='none', facecolor='#e0e0e0', zorder=1))
    ax.plot([x_center-r2_draw, x_center-r2_draw], [y_base, y_mid], color='black', zorder=2)
    ax.plot([x_center+r2_draw, x_center+r2_draw], [y_base, y_mid], color='black', zorder=2)

    # Elipse media (top de abajo / base de arriba) - Parte visible del grande
    ax.add_patch(patches.Ellipse((x_center, y_mid), r2_draw*2, 0.6, edgecolor='black', facecolor='#e0e0e0', zorder=3))

    # Arriba
    # Cuerpo
    ax.add_patch(patches.Rectangle((x_center-r1_draw, y_mid), r1_draw*2, (y_top-y_mid), edgecolor='none', facecolor='#c0c0c0', zorder=4))
    ax.plot([x_center-r1_draw, x_center-r1_draw], [y_mid, y_top], color='black', zorder=5)
    ax.plot([x_center+r1_draw, x_center+r1_draw], [y_mid, y_top], color='black', zorder=5)
    # Elipse base arriba (oculta parcialmente) - Dibujamos arco o elipse completa relleno gris
    ax.add_patch(patches.Ellipse((x_center, y_mid), r1_draw*2, 0.5, edgecolor='black', facecolor='#c0c0c0', zorder=6))
    # Elipse top
    ax.add_patch(patches.Ellipse((x_center, y_top), r1_draw*2, 0.5, edgecolor='black', facecolor='#c0c0c0', zorder=7))

    # COTAS

    # Cota Altura (Lado derecho)
    # Línea vertical total
    ax.annotate("", xy=(x_center+r2_draw+0.5, y_base), xytext=(x_center+r2_draw+0.5, y_mid), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(x_center+r2_draw+0.6, (y_base+y_mid)/2, f"h = {h_val} cm", va='center')

    ax.annotate("", xy=(x_center+r2_draw+0.5, y_mid), xytext=(x_center+r2_draw+0.5, y_top), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(x_center+r2_draw+0.6, (y_mid+y_top)/2, f"h = {h_val} cm", va='center')

    # Cota Radio (Arriba)
    # Radio superior
    ax.annotate("", xy=(x_center, y_top), xytext=(x_center+r1_draw, y_top), arrowprops=dict(arrowstyle="<->", lw=1), zorder=20)
    ax.text(x_center + r1_draw/2, y_top + 0.4, f"r = {r1_val} cm", ha='center')

    # Radio inferior (Abajo, un poco desplazado)
    ax.annotate("", xy=(x_center, y_base-0.5), xytext=(x_center+r2_draw, y_base-0.5), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(x_center + r2_draw/2, y_base - 0.8, f"r = {r2_val} cm", ha='center')
    # Líneas guía radio inferior
    ax.plot([x_center, x_center], [y_base, y_base-0.5], 'k--', lw=0.5)
    ax.plot([x_center+r2_draw, x_center+r2_draw], [y_base, y_base-0.5], 'k--', lw=0.5)

    ax.set_xlim(0, 8)
    ax.set_ylim(0, 6.5)
    ax.set_aspect('equal')
    ax.axis('off')

    plt.savefig(output_path, bbox_inches='tight', dpi=100)
    plt.close()
    print(f"Generated {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["squares", "boxplot", "cylinders"])
    parser.add_argument("--output", required=True)
def draw_scatter_q58(data, mean_val, output_path):
    """
    Genera Scatter Plot para Q58 (Edades futbolistas).
    data: dict { 'Country': [ages...] }
    mean_val: float (Promedio general para línea horizontal)
    """
    fig, ax = plt.subplots(figsize=(6, 5))

    countries = list(data.keys())
    x_positions = range(len(countries))

    # Plot points
    for i, country in enumerate(countries):
        ages = data[country]
        x_vals = [i] * len(ages)
        ax.scatter(x_vals, ages, color='black', s=20, zorder=3)

    # Mean line
    ax.axhline(y=mean_val, color='black', linestyle='-', linewidth=1, zorder=2)
    # ax.text(len(countries)-0.5, mean_val + 0.5, f"Promedio\n{mean_val}", va='bottom', ha='right', fontsize=9)

    # Styling
    ax.set_xticks(x_positions)
    ax.set_xticklabels(countries)
    ax.set_ylabel("Edad en años")

    # Grid lines horizontal only
    ax.yaxis.grid(True, linestyle='--', alpha=0.5)

    # Spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.savefig(output_path, bbox_inches='tight', dpi=120)
    plt.close()
    print(f"Generated {output_path}")

def draw_double_pie_q55(data1, data2, output_path):
    """
    Genera dos gráficos de torta lado a lado para Q55 (Fonasa).
    data1: dict {label: percent} (Previsión)
    data2: dict {label: percent} (Tramos Fonasa)
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

    def bake_pie(ax, data, title):
        labels = list(data.keys())
        sizes = list(data.values())
        # Colores grisáceos/neutros estilo prueba
        colors = ['#e0e0e0', '#c0c0c0', '#a0a0a0', '#ffffff', '#f0f0f0'][:len(labels)]

        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.0f %%',
                                          startangle=90, colors=colors,
                                          wedgeprops=dict(edgecolor='black'))
        ax.set_title(title, fontsize=10, pad=10)

    bake_pie(ax1, data1, "Distribución población\npor tipo previsión")
    bake_pie(ax2, data2, "Distribución población\nFonasa por tramo")

    plt.savefig(output_path, bbox_inches='tight', dpi=100)
    plt.close()
    print(f"Generated {output_path}")

def draw_pie_q23(data, center_text, output_path):
    """
    Genera gráfico de torta simple para Q23 (Electricidad).
    data: dict {label: percent}
    center_text: str (Texto en el centro o título)
    """
    fig, ax = plt.subplots(figsize=(6, 5))

    labels = list(data.keys())
    sizes = list(data.values())
    colors = ['#ffffff', '#f0f0f0', '#e0e0e0', '#d0d0d0', '#c0c0c0', '#b0b0b0', '#a0a0a0', '#909090'][:len(labels)]

    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.0f%%',
                                      startangle=140, colors=colors, pctdistance=0.85,
                                      wedgeprops=dict(edgecolor='black'))

    # Donut style or just Pie? Q23 original is Donut-ish or lists total in center?
    # Original description: "Gráfico circular... En el centro se lee '80 155 GWh'" -> Donut chart
    centre_circle = plt.Circle((0,0),0.60,fc='white')
    fig.gca().add_artist(centre_circle)

    ax.text(0, 0, center_text, ha='center', va='center', fontsize=10, fontweight='bold')

    plt.savefig(output_path, bbox_inches='tight', dpi=100)
    plt.close()
    print(f"Generated {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate geometric variant images")
    parser.add_argument("--type", required=True, choices=["squares", "boxplot", "cylinders", "scatter_q58", "pie_q55", "pie_q23"])
    parser.add_argument("--output", required=True, help="Output image path")

    parser.add_argument("--squares-n", type=int, default=10)
    # Stats for boxplot: min,q1,med,q3,max
    parser.add_argument("--stats", type=float, nargs=5)

    # Params for cylinders
    parser.add_argument("--cyl-h", type=float, default=10)
    parser.add_argument("--cyl-r1", type=float, default=6)
    parser.add_argument("--cyl-r2", type=float, default=8)

    # Params for Scatter Q58 (JSON string for data dict)
    parser.add_argument("--scatter-data", type=str, help="JSON dict for scatter data") # '{"Chile": [20,21], ...}'
    parser.add_argument("--scatter-mean", type=float, help="Mean value line")

    # Params for Pies (JSON string)
    parser.add_argument("--pie-data1", type=str, help="JSON dict for pie 1")
    parser.add_argument("--pie-data2", type=str, help="JSON dict for pie 2")
    parser.add_argument("--pie-center", type=str, help="Center text for Q23 pie")

    args = parser.parse_args()

    import json

    if args.type == "squares":
        draw_square_figure(args.squares_n, args.output)
    elif args.type == "boxplot":
        if not args.stats:
            print("Error: --stats required for boxplot")
            sys.exit(1)
        draw_boxplot(args.stats, args.output)
    elif args.type == "cylinders":
        draw_cylinders(args.output, args.cyl_h, args.cyl_r1, args.cyl_r2)
    elif args.type == "scatter_q58":
        if not args.scatter_data or not args.scatter_mean:
            print("Error: --scatter-data and --scatter-mean required")
            sys.exit(1)
        data = json.loads(args.scatter_data)
        draw_scatter_q58(data, args.scatter_mean, args.output)
    elif args.type == "pie_q55":
        if not args.pie_data1 or not args.pie_data2:
            print("Error: --pie-data1 and --pie-data2 required")
            sys.exit(1)
        d1 = json.loads(args.pie_data1)
        d2 = json.loads(args.pie_data2)
        draw_double_pie_q55(d1, d2, args.output)
    elif args.type == "pie_q23":
        if not args.pie_data1:
             print("Error: --pie-data1 required")
             sys.exit(1)
        d1 = json.loads(args.pie_data1)
        center = args.pie_center if args.pie_center else ""
        draw_pie_q23(d1, center, args.output)
