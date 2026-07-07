"""
Generate dim_bahan.csv — master data bahan baku (dimension table).
Konsisten dengan fact_transaksi (bahan_id 1-5000, kategori & satuan sama persis)
karena pakai seed & urutan random yang sama dengan script generate_transaksi_bahan.py.

Cara pakai:
    python generate_dim_bahan.py
Hasil: dim_bahan.csv di folder yang sama.
"""

import pandas as pd
import numpy as np
from faker import Faker

fake = Faker("id_ID")
np.random.seed(42)

JUMLAH_BAHAN = 5000

# HARUS SAMA PERSIS dengan script fact_transaksi (kategori, satuan, range harga)
KATEGORI_BAHAN = [
    ("Bahan Pokok", "kg", 5_000, 25_000),
    ("Bahan Kemasan", "pcs", 200, 3_000),
    ("Bahan Tambahan/Aditif", "kg", 15_000, 80_000),
    ("Bahan Cair", "liter", 8_000, 40_000),
    ("Bahan Pendukung", "dus", 30_000, 150_000),
]

# Panggilan random pertama ini HARUS identik urutannya dengan script fact_transaksi
# supaya bahan_id 1-5000 dapat kategori yang sama persis di kedua tabel.
bahan_kategori_idx = np.random.choice(len(KATEGORI_BAHAN), size=JUMLAH_BAHAN)

nama_kategori = np.array([KATEGORI_BAHAN[k][0] for k in bahan_kategori_idx])
satuan = np.array([KATEGORI_BAHAN[k][1] for k in bahan_kategori_idx])

# Nama bahan dummy tapi kelihatan real, mengikuti kategori
NAMA_PER_KATEGORI = {
    "Bahan Pokok": ["Tepung terigu", "Gula pasir", "Beras", "Garam", "Tapioka", "Minyak sawit", "Kedelai"],
    "Bahan Kemasan": ["Botol plastik 500ml", "Kardus karton", "Label stiker", "Tutup botol", "Plastik wrap", "Kaleng"],
    "Bahan Tambahan/Aditif": ["Pengawet natrium benzoat", "Pewarna makanan", "Perisa vanila", "Pengemulsi", "Vitamin C"],
    "Bahan Cair": ["Minyak goreng", "Sirup fruktosa", "Susu cair", "Air demineralisasi", "Konsentrat jus"],
    "Bahan Pendukung": ["Kotak display", "Pallet kayu", "Selotip industri", "Karung goni", "Lakban"],
}

nama_bahan = [
    f"{np.random.choice(NAMA_PER_KATEGORI[nama_kategori[i]])} - varian {i%37+1}"
    for i in range(JUMLAH_BAHAN)
]

# Stok minimum & maksimum — dibuat variatif per bahan, dalam skala yang masuk akal
# dibanding volume transaksi mingguan (ribuan-puluhan ribu unit).
stok_minimum = np.random.randint(3000, 15000, size=JUMLAH_BAHAN)
stok_maksimum = stok_minimum + np.random.randint(10000, 40000, size=JUMLAH_BAHAN)

# Sengaja bikin ~15% bahan dengan stok_minimum jauh lebih tinggi
# biar ada kasus "kritis" yang realistis buat didemokan di portofolio
idx_kritis = np.random.choice(JUMLAH_BAHAN, size=int(JUMLAH_BAHAN * 0.15), replace=False)
stok_minimum[idx_kritis] = np.random.randint(15000, 30000, size=len(idx_kritis))

df = pd.DataFrame({
    "bahan_id": np.arange(1, JUMLAH_BAHAN + 1),
    "nama_bahan": nama_bahan,
    "kategori": nama_kategori,
    "satuan": satuan,
    "stok_minimum": stok_minimum,
    "stok_maksimum": stok_maksimum,
})

df.to_csv("dim_bahan.csv", index=False)
print(f"Selesai! {len(df)} baris master bahan tersimpan ke dim_bahan.csv")
print(df.head(10).to_string())
