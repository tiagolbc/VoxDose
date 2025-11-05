# voxdose_reports/plots_spl_dba.py
import matplotlib.pyplot as plt

def render_spl_dba_plot(window_time, dBA, t, out_png="SPL_dBA_plot.png"):
    # Plotting dBA
    plt.figure(3)
    plt.clf()
    plt.plot(window_time, dBA, linewidth=2)
    plt.title('A-weighted Sound Level')
    plt.xlabel('Time (sec.)')
    plt.ylabel('Sound Level (dBA)')
    plt.xlim([t[0], t[-1]])
    plt.grid(True)
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.show()
