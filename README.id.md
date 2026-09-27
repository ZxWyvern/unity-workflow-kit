# Unity Workflow Agent Generator

Beri coding agent panduan kecil yang spesifik untuk proyek Unity Anda: mulai dari mana, file mana yang memiliki state, apa yang harus dijaga, dan cara memeriksa hasilnya.

[![Proyek Unity](https://img.shields.io/badge/Unity-181B23?style=for-the-badge&logo=unity&logoColor=FFFFFF)](https://unity.com/)
[![Helper Python 3.9+](https://img.shields.io/badge/Python_3.9%2B-181B23?style=for-the-badge&logo=python&logoColor=FFD43B)](https://www.python.org/)
[![Dokumen workflow Markdown](https://img.shields.io/badge/Markdown-181B23?style=for-the-badge&logo=markdown&logoColor=FFFFFF)](https://daringfireball.net/projects/markdown/)
[![Pelacakan perubahan Git](https://img.shields.io/badge/Git-181B23?style=for-the-badge&logo=git&logoColor=F05032)](https://git-scm.com/)
[![CI GitHub Actions](https://img.shields.io/badge/GitHub_Actions-181B23?style=for-the-badge&logo=githubactions&logoColor=58A6FF)](https://github.com/features/actions)

[English](README.md) · [Panduan lengkap](docs/USAGE.md) · [Kontribusi](CONTRIBUTING.md)

**v1.3.0 beta.** Tool Python lokal sudah diuji. Kualitas generasi dan biaya token lintas proyek serta host AI masih membutuhkan laporan penggunaan nyata. Tidak berafiliasi dengan Unity Technologies.

## Mulai dengan satu prompt

1. Unduh ZIP repositori dan ekstrak di proyek Unity sebagai `_ai-generator/`, di luar `Assets/`. Folder di samping proyek juga bisa; sesuaikan path pada prompt.
2. Buka proyek Unity melalui coding agent yang dapat membaca file lokal.
3. Tempel:

```text
Baca _ai-generator/ENTRYPOINT.md dan siapkan workflow untuk proyek Unity ini.
```

Agent menemukan proyek, membuat pack Compact, atau memperbarui pack yang sudah ada. Arsitektur mengikuti proyek Anda. Periksa diff lalu commit pack dan bagian bertanda di `AGENTS.md`.

Helper memakai Python 3.9+ dan standard library, tanpa dependensi tambahan. Kalau Python tidak tersedia, agent mengikuti prosedur manual dan menyatakan validator belum dijalankan. Tambahkan `_ai-generator/` ke `.gitignore` proyek jika kit tidak ingin di-commit.

**Chat yang hanya menerima upload:** lampirkan export proyek dan [bundle lengkap](dist/Unity_Workflow_Agent_Generator_bundle.md), lalu minta penyiapan workflow. Bundle menyertakan source tool sehingga konteks masuk lebih besar. Untuk agent dengan akses filesystem, gunakan folder kit.

## Cara menghemat konteks

- Baca entrypoint dan tiga referensi wajib; modul lain dibaca sesuai kebutuhan.
- Mulai dari maksimal 2 subsistem, 1 alur menyeluruh, 3 temuan, 3 route, dan 1 langkah berikutnya. Perluas jika dependensi nyata membutuhkan pemeriksaan.
- Targetkan instruksi startup sekitar 20 baris dan `agent.md` sekitar 80 baris.
- Ambil route, dependensi bukti, check, dan area terlindungi melalui `context.py`. Seluruh pack tidak perlu masuk ke konteks model.
- Refresh klaim yang terdampak perubahan; biarkan isi lain tetap.

Ini mekanisme pembatas konteks, bukan jaminan persentase penghematan token. Biaya aktual bergantung pada agent, tugas, dan proyek. Instruksi yang berlaku serta verifikasi yang diperlukan tetap harus dibaca dan dijalankan sesuai izin.

## File yang dihasilkan

`AGENTS.md` mendapat bagian startup dengan marker; aturan yang sudah ada dipertahankan.

```text
docs/ai-workflow/
  agent.md                      prosedur, route tugas, langkah berikutnya
  project-context.md            klaim, area terlindungi, temuan, cakupan
  validation-matrix.md          check dan hasilnya
  session-handoff.md            pekerjaan saat ini dan langkah selanjutnya
  index.json                    navigasi
  tools/                        empat helper Python kecil
```

Standard menambahkan README dan file workflow terpisah jika diperlukan. Extended menambahkan kontrak khusus yang relevan. Bagian tertentu dari repositori besar tetap bisa memakai Compact.

Generasi menulis dokumentasi workflow dan helper. Implementasi gameplay membutuhkan permintaan terpisah. Keberadaan source, wiring scene, dan hasil runtime dicatat sebagai klaim berbeda.

## Pemakaian harian

```text
Baca AGENTS.md dan docs/ai-workflow/agent.md. Implementasikan: <tugas Anda>.
Muat route dan dependensi yang relevan saja. Laporkan check yang dijalankan dan belum dijalankan.
```

Agent dapat memilih konteks melalui:

```bash
python docs/ai-workflow/tools/context.py .
python docs/ai-workflow/tools/context.py . --route R-001
```

Gunakan ID dari pack Anda. Ulangi `--route` jika tugas mencakup beberapa route. Batas keluaran default adalah 16.000 karakter; jika terlalu besar, tool berhenti dengan penjelasan, tanpa memotong bukti diam-diam. Baca blok aslinya atau naikkan `--max-chars` jika diperlukan.

## Proyek besar dan tim

Tambahkan fokus:

```text
Focus: inventory save/load. Unity root: games/client.
```

Agent mencari path dulu, membaca subsistem terkait beserta dependensinya, dan mencatat sisanya sebagai belum diperiksa. Cache dan kumpulan aset vendor tidak ikut pencarian luas. Jika ada beberapa root Unity, pilih berdasarkan tugas atau tentukan root secara eksplisit.

| Pengaturan opsional | Kegunaan |
|---|---|
| `budget = lean` | Default, investigasi terfokus |
| `budget = balanced` | Cakupan sistem lebih luas |
| `budget = deep` | Verifikasi lebih dalam pada jalur terpilih; perluasan cakupan disebutkan eksplisit |
| `architecture_policy = toward: <target>` | Target eksplisit untuk kode baru atau yang disentuh |

Setelah merge atau perubahan besar:

```text
Baca _ai-generator/ENTRYPOINT.md dan refresh workflow pack yang sudah ada.
```

Untuk CI tim:

```bash
python docs/ai-workflow/tools/validate_pack.py . docs/ai-workflow
```

Validator memeriksa struktur dan konsistensi, bukan membuktikan gameplay benar. Refresh Git mencakup file baru yang belum di-track dan tidak di-ignore. Snapshot dirty serta perubahan environment tetap perlu diperiksa eksplisit.

## Pengembangan kit

```bash
python tests/run_tests.py
python tools/bundle.py
```

CI dikonfigurasi untuk Python 3.9 dan 3.12 di Linux serta Windows, termasuk pemeriksaan bundle. Lihat [CHANGELOG.md](CHANGELOG.md) untuk migrasi dan [lisensi MIT](LICENSE).
