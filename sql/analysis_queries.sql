-- =====================================================================
-- INVENTORY MANAGEMENT ANALYSIS — FMCG Raw Material Restock Alert System
-- Dijalankan di DuckDB
-- =====================================================================


-- =====================================================================
-- 1. LOAD DATA — dari hasil generate_transaksi_bahan.py & generate_dim_bahan.py
-- =====================================================================

CREATE TABLE fact_transaksi AS
SELECT * FROM 'transaksi_bahan_1minggu.csv';

CREATE TABLE dim_bahan AS
SELECT * FROM 'dim_bahan.csv';

-- Cek jumlah baris ter-load
SELECT COUNT(*) FROM fact_transaksi;   -- harus 500.000
SELECT COUNT(*) FROM dim_bahan;        -- harus 5.000


-- =====================================================================
-- 2. EKSPLORASI DATA AWAL
-- =====================================================================

DESCRIBE fact_transaksi;

SELECT * FROM fact_transaksi LIMIT 10;

-- Distribusi jenis transaksi (validasi proporsi MASUK/KELUAR/TRANSFER/RETUR)
SELECT jenis_transaksi, COUNT(*) AS jumlah,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS persentase
FROM fact_transaksi
GROUP BY jenis_transaksi
ORDER BY jumlah DESC;

-- Total transaksi & nilai per hari (validasi pola weekday vs weekend)
SELECT tanggal,
       COUNT(*) AS jumlah_transaksi,
       SUM(total_nilai) AS total_nilai
FROM fact_transaksi
GROUP BY tanggal
ORDER BY tanggal;

-- Bahan baku dengan transaksi terbanyak
SELECT bahan_id, COUNT(*) AS jumlah_transaksi
FROM fact_transaksi
GROUP BY bahan_id
ORDER BY jumlah_transaksi DESC
LIMIT 10;


-- =====================================================================
-- 3. RESTOCK ALERT — deteksi status stok (KRITIS / WARNING / AMAN)
-- =====================================================================

COPY (
    SELECT
        d.bahan_id, d.nama_bahan, d.kategori, d.satuan,
        d.stok_minimum, d.stok_maksimum,
        SUM(CASE WHEN f.jenis_transaksi = 'MASUK' THEN f.jumlah
                 WHEN f.jenis_transaksi = 'KELUAR' THEN -f.jumlah
                 WHEN f.jenis_transaksi = 'RETUR' THEN f.jumlah
                 ELSE 0 END) AS stok_bersih_minggu_ini,
        CASE
            WHEN SUM(CASE WHEN f.jenis_transaksi = 'MASUK' THEN f.jumlah
                          WHEN f.jenis_transaksi = 'KELUAR' THEN -f.jumlah
                          WHEN f.jenis_transaksi = 'RETUR' THEN f.jumlah
                          ELSE 0 END) < d.stok_minimum THEN 'KRITIS'
            WHEN SUM(CASE WHEN f.jenis_transaksi = 'MASUK' THEN f.jumlah
                          WHEN f.jenis_transaksi = 'KELUAR' THEN -f.jumlah
                          WHEN f.jenis_transaksi = 'RETUR' THEN f.jumlah
                          ELSE 0 END) < d.stok_minimum * 1.2 THEN 'WARNING'
            ELSE 'AMAN'
        END AS status_stok
    FROM fact_transaksi f
    JOIN dim_bahan d ON f.bahan_id = d.bahan_id
    GROUP BY d.bahan_id, d.nama_bahan, d.kategori, d.satuan, d.stok_minimum, d.stok_maksimum
) TO 'hasil_restock_alert.csv' (HEADER, DELIMITER ',');

-- Preview: bahan dengan status kritis/warning saja
SELECT
    d.bahan_id, d.nama_bahan, d.kategori,
    SUM(CASE WHEN f.jenis_transaksi = 'MASUK' THEN f.jumlah
             WHEN f.jenis_transaksi = 'KELUAR' THEN -f.jumlah
             WHEN f.jenis_transaksi = 'RETUR' THEN f.jumlah
             ELSE 0 END) AS stok_bersih,
    d.stok_minimum
FROM fact_transaksi f
JOIN dim_bahan d ON f.bahan_id = d.bahan_id
GROUP BY d.bahan_id, d.nama_bahan, d.kategori, d.stok_minimum
HAVING stok_bersih < d.stok_minimum * 1.2
ORDER BY stok_bersih ASC
LIMIT 30;


-- =====================================================================
-- 4. TREN TRANSAKSI HARIAN
-- =====================================================================

COPY (
    SELECT
        tanggal,
        jenis_transaksi,
        COUNT(*) AS jumlah_transaksi,
        SUM(total_nilai) AS total_nilai
    FROM fact_transaksi
    GROUP BY tanggal, jenis_transaksi
    ORDER BY tanggal, jenis_transaksi
) TO 'tren_harian.csv' (HEADER, DELIMITER ',');


-- =====================================================================
-- 5. REKAP STATUS STOK PER KATEGORI
-- =====================================================================

COPY (
    WITH stok_per_bahan AS (
        SELECT
            d.bahan_id, d.kategori, d.stok_minimum,
            SUM(CASE WHEN f.jenis_transaksi = 'MASUK' THEN f.jumlah
                     WHEN f.jenis_transaksi = 'KELUAR' THEN -f.jumlah
                     WHEN f.jenis_transaksi = 'RETUR' THEN f.jumlah
                     ELSE 0 END) AS stok_bersih
        FROM fact_transaksi f
        JOIN dim_bahan d ON f.bahan_id = d.bahan_id
        GROUP BY d.bahan_id, d.kategori, d.stok_minimum
    )
    SELECT
        kategori,
        COUNT(*) AS total_bahan,
        SUM(CASE WHEN stok_bersih < stok_minimum THEN 1 ELSE 0 END) AS jumlah_kritis,
        SUM(CASE WHEN stok_bersih >= stok_minimum AND stok_bersih < stok_minimum * 1.2 THEN 1 ELSE 0 END) AS jumlah_warning,
        SUM(CASE WHEN stok_bersih >= stok_minimum * 1.2 THEN 1 ELSE 0 END) AS jumlah_aman
    FROM stok_per_bahan
    GROUP BY kategori
    ORDER BY jumlah_kritis DESC
) TO 'rekap_kategori.csv' (HEADER, DELIMITER ',');


-- =====================================================================
-- 6. PREDIKSI HARI KEHABISAN STOK
-- =====================================================================

COPY (
    SELECT
        d.bahan_id, d.nama_bahan, d.kategori, d.stok_minimum,
        SUM(CASE WHEN f.jenis_transaksi = 'MASUK' THEN f.jumlah
                 WHEN f.jenis_transaksi = 'KELUAR' THEN -f.jumlah
                 WHEN f.jenis_transaksi = 'RETUR' THEN f.jumlah
                 ELSE 0 END) AS stok_saat_ini,
        SUM(CASE WHEN f.jenis_transaksi = 'KELUAR' THEN f.jumlah ELSE 0 END) / 7.0 AS rata_rata_keluar_per_hari,
        ROUND(
            SUM(CASE WHEN f.jenis_transaksi = 'MASUK' THEN f.jumlah
                     WHEN f.jenis_transaksi = 'KELUAR' THEN -f.jumlah
                     WHEN f.jenis_transaksi = 'RETUR' THEN f.jumlah
                     ELSE 0 END)
            / NULLIF(SUM(CASE WHEN f.jenis_transaksi = 'KELUAR' THEN f.jumlah ELSE 0 END) / 7.0, 0)
        , 1) AS perkiraan_habis_dalam_hari
    FROM fact_transaksi f
    JOIN dim_bahan d ON f.bahan_id = d.bahan_id
    GROUP BY d.bahan_id, d.nama_bahan, d.kategori, d.stok_minimum
    HAVING perkiraan_habis_dalam_hari IS NOT NULL
    ORDER BY perkiraan_habis_dalam_hari ASC
) TO 'prediksi_habis.csv' (HEADER, DELIMITER ',');

-- Preview: bahan yang diperkirakan paling cepat habis
SELECT bahan_id, nama_bahan, perkiraan_habis_dalam_hari
FROM 'prediksi_habis.csv'
ORDER BY perkiraan_habis_dalam_hari ASC
LIMIT 10;


-- =====================================================================
-- 7. TOP SUPPLIER BERDASARKAN NILAI PEMBELIAN
-- =====================================================================

COPY (
    SELECT
        supplier_id,
        COUNT(*) AS jumlah_transaksi,
        SUM(total_nilai) AS total_nilai_pembelian
    FROM fact_transaksi
    WHERE jenis_transaksi = 'MASUK'
    GROUP BY supplier_id
    ORDER BY total_nilai_pembelian DESC
    LIMIT 50
) TO 'top_supplier.csv' (HEADER, DELIMITER ',');
