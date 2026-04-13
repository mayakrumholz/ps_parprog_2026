import matplotlib.pyplot as plt

# Messdaten aus perf
n = [512, 1024, 2048]

# Variante 0: j außen, i innen
load_v0 = [444, 753962, 7780523]
store_v0 = [136, 336807, 4146135]
time_v0 = [0.007024509, 0.033429724, 0.181725296]

# Variante 1: i außen, j innen
load_v1 = [81, 5799, 139804]
store_v1 = [1, 20, 77]
time_v1 = [0.003961967, 0.010746731, 0.034410404]

# -----------------------------
# Grafik 1: LLC-load-misses
# -----------------------------
plt.figure(figsize=(7, 5))
plt.plot(n, load_v0, marker="o", label="v0: j außen, i innen")
plt.plot(n, load_v1, marker="o", label="v1: i außen, j innen")
plt.xscale("log", base=2)
plt.yscale("log")
plt.xlabel("Matrixgröße n")
plt.ylabel("LLC-load-misses")
plt.title("LLC-load-misses des Hadamard-Produkts")
plt.legend()
plt.tight_layout()
plt.savefig("llc_load_misses.png", dpi=300)
plt.show()

# -----------------------------
# Grafik 2: LLC-store-misses
# -----------------------------
plt.figure(figsize=(7, 5))
plt.plot(n, store_v0, marker="o", label="v0: j außen, i innen")
plt.plot(n, store_v1, marker="o", label="v1: i außen, j innen")
plt.xscale("log", base=2)
plt.yscale("log")
plt.xlabel("Matrixgröße n")
plt.ylabel("LLC-store-misses")
plt.title("LLC-store-misses des Hadamard-Produkts")
plt.legend()
plt.tight_layout()
plt.savefig("llc_store_misses.png", dpi=300)
plt.show()

# -----------------------------
# Grafik 3: Laufzeit
# -----------------------------
plt.figure(figsize=(7, 5))
plt.plot(n, time_v0, marker="o", label="v0: j außen, i innen")
plt.plot(n, time_v1, marker="o", label="v1: i außen, j innen")
plt.xscale("log", base=2)
plt.yscale("log")
plt.xlabel("Matrixgröße n")
plt.ylabel("Laufzeit in Sekunden")
plt.title("Laufzeit des Hadamard-Produkts")
plt.legend()
plt.tight_layout()
plt.savefig("runtime.png", dpi=300)
plt.show()