#!/usr/bin/env python3
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

sim = AerSimulator()
tqc = transpile(qc, sim)
result = sim.run(tqc, shots=256).result()
print({"ok": True, "backend": "aer_simulator", "counts": result.get_counts()})
