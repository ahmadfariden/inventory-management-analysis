"""
Generate data dummy transaksi bahan baku (inbound/outbound) skala enterprise FMCG.
Output: CSV dengan 500.000 baris, 14 kolom, rentang waktu 1 minggu.

Cara pakai (di cmd/terminal laptop kamu):
    pip install pandas numpy faker
    python generate_transaksi_bahan.py

Hasil: file 'transaksi_bahan_1minggu.csv' di folder yang sama.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("id_ID")
np.random.seed(42)

# ======================
# KONFIGURASI SKALA
# ======================
TOTAL_BARIS = 500_000
JUMLAH_BAHAN = 5000        # jumlah SKU bahan baku
JUMLAH_SUPPLIER = 300
JUMLAH_GUDANG = 200
JUMLAH_USER = 150
TANGGAL_MULAI = datetime(2026, 6, 29)  # Senin
HARI_DALAM_MINGGU = 7

# Proporsi jenis transaksi (realistis: keluar lebih sering dari masuk)
PROPORSI_TRANSAKSI = {
    "MASUK": 0.40,
    "KELUAR": 0.55,
    "TRANSFER": 0.03,
    "RETUR": 0.02,
}

# Kategori bahan baku (buat variasi harga & satuan yang masuk akal)
KATEGORI_BAHAN = [
    ("Bahan Pokok", "kg", 5_000, 25_000),
    ("Bahan Kemasan", "pcs", 200, 3_000),
    ("Bahan Tambahan/Aditif", "kg", 15_000, 80_000),
    ("Bahan Cair", "liter", 8_000, 40_000),
    ("Bahan Pendukung", "dus", 30_000, 150_000),
]

STATUS_APPROVAL = ["APPROVED", "APPROVED", "APPROVED", "PENDING", "REJECTED"]  # approved dominan

# ======================
# BIKIN MASTER DATA (referensi id)
# ======================
print("Menyiapkan master data bahan, supplier, gudang, user...")

bahan_kategori = np.random.choice(len(KATEGORI_BAHAN), size=JUMLAH_BAHAN)
bahan_harga_min = np.array([KATEGORI_BAHAN[k][2] for k in bahan_kategori])
bahan_harga_max = np.array([KATEGORI_BAHAN[k][3] for k in bahan_kategori])
bahan_satuan = np.array([KATEGORI_BAHAN[k][1] for k in bahan_kategori])

supplier_ids = np.arange(1, JUMLAH_SUPPLIER + 1)
gudang_ids = np.arange(1, JUMLAH_GUDANG + 1)
user_ids = np.arange(1, JUMLAH_USER + 1)

# ======================
# GENERATE TRANSAKSI
# ======================
print(f"Generate {TOTAL_BARIS:,} baris transaksi...")

# 1. tanggal & waktu -> lebih ramai di jam kerja (08:00-17:00), weekday > weekend
hari_offset = np.random.choice(
    HARI_DALAM_MINGGU,
    size=TOTAL_BARIS,
    p=[0.17, 0.17, 0.17, 0.17, 0.16, 0.08, 0.08]  # senin-jumat lebih ramai dari sabtu-minggu
)
tanggal = [TANGGAL_MULAI + timedelta(days=int(d)) for d in hari_offset]

jam = np.clip(np.random.normal(loc=12, scale=3, size=TOTAL_BARIS), 6, 21).astype(int)
menit = np.random.randint(0, 60, size=TOTAL_BARIS)
detik = np.random.randint(0, 60, size=TOTAL_BARIS)
waktu = [f"{h:02d}:{m:02d}:{s:02d}" for h, m, s in zip(jam, menit, detik)]

# 2. bahan_id, supplier_id, gudang_id, user_id
bahan_id = np.random.randint(1, JUMLAH_BAHAN + 1, size=TOTAL_BARIS)
idx_bahan = bahan_id - 1  # buat lookup kategori/harga
supplier_id = np.random.choice(supplier_ids, size=TOTAL_BARIS)
gudang_id = np.random.choice(gudang_ids, size=TOTAL_BARIS)
user_input_id = np.random.choice(user_ids, size=TOTAL_BARIS)

# 3. jenis transaksi sesuai proporsi
jenis_transaksi = np.random.choice(
    list(PROPORSI_TRANSAKSI.keys()),
    size=TOTAL_BARIS,
    p=list(PROPORSI_TRANSAKSI.values())
)

# 4. satuan (ikut kategori bahan)
satuan = bahan_satuan[idx_bahan]

# 5. jumlah (beda skala tergantung jenis transaksi: masuk biasanya lebih besar dari keluar harian)
jumlah = np.where(
    jenis_transaksi == "MASUK",
    np.random.randint(50, 2000, size=TOTAL_BARIS),
    np.random.randint(5, 300, size=TOTAL_BARIS)
).astype(float)

# 6. harga satuan (random dalam range kategori bahan masing-masing)
harga_satuan = np.random.randint(bahan_harga_min[idx_bahan], bahan_harga_max[idx_bahan] + 1)

# 7. total nilai
total_nilai = jumlah * harga_satuan

# 8. nomor referensi (beda format tergantung jenis transaksi)
def buat_referensi(jenis, i):
    if jenis == "MASUK":
        return f"PO-{tanggal[i].strftime('%Y%m')}-{i%99999:05d}"
    elif jenis == "KELUAR":
        return f"WO-{tanggal[i].strftime('%Y%m')}-{i%99999:05d}"
    elif jenis == "TRANSFER":
        return f"TRF-{tanggal[i].strftime('%Y%m')}-{i%99999:05d}"
    else:
        return f"RTN-{tanggal[i].strftime('%Y%m')}-{i%99999:05d}"

nomor_referensi = [buat_referensi(jenis_transaksi[i], i) for i in range(TOTAL_BARIS)]

# 9. status approval (approved dominan, sedikit pending/rejected)
status_approval = np.random.choice(STATUS_APPROVAL, size=TOTAL_BARIS)

# ======================
# SUSUN JADI DATAFRAME (14 KOLOM)
# ======================
print("Menyusun dataframe...")

df = pd.DataFrame({
    "transaksi_id": np.arange(1, TOTAL_BARIS + 1),
    "tanggal": [t.strftime("%Y-%m-%d") for t in tanggal],
    "waktu": waktu,
    "bahan_id": bahan_id,
    "supplier_id": supplier_id,
    "gudang_id": gudang_id,
    "jenis_transaksi": jenis_transaksi,
    "jumlah": jumlah,
    "satuan": satuan,
    "harga_satuan": harga_satuan,
    "total_nilai": total_nilai,
    "nomor_referensi": nomor_referensi,
    "user_input_id": user_input_id,
    "status_approval": status_approval,
})

# urutkan berdasarkan tanggal+waktu biar mirip log transaksi asli
df["_sort_key"] = pd.to_datetime(df["tanggal"] + " " + df["waktu"])
df = df.sort_values("_sort_key").drop(columns="_sort_key").reset_index(drop=True)
df["transaksi_id"] = np.arange(1, TOTAL_BARIS + 1)  # re-id biar urut

# ======================
# SIMPAN KE CSV
# ======================
output_file = "transaksi_bahan_1minggu.csv"
df.to_csv(output_file, index=False)

print(f"\nSelesai! File tersimpan: {output_file}")
print(f"Total baris: {len(df):,}")
print(f"Total kolom: {len(df.columns)}")
print("\nPreview data:")
print(df.head(10).to_string())
print("\nDistribusi jenis transaksi:")
print(df["jenis_transaksi"].value_counts(normalize=True).round(3))
