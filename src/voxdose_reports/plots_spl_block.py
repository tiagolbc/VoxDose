import matplotlib.pyplot as plt

def render_spl_plot(window_time, dB, t, out_png="SPL_plot.png"):
    plt.figure(3)
    plt.clf()
    plt.plot(window_time, dB, linewidth=2)
    plt.title('A-weighted Sound Level')
    plt.xlabel('Time (sec.)')
    plt.ylabel('Sound Level (dBA)')
    plt.xlim([t[0], t[-1]])
    plt.grid(True)
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    # no plt.show() here (keep headless-friendly)

