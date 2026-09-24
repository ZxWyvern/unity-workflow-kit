# Unity Workflow Agent Generator

**Biarkan AI coding agent Anda menulis workflow yang spesifik dan berbasis bukti untuk proyek Unity *Anda*, langsung dari file aslinya.**

Bukan prompt generik "jadilah senior Unity developer". Kit ini membuat AI memeriksa proyek Anda (scene, prefab, package, source, test) lalu menghasilkan **workflow pack** kecil di `docs/ai-workflow/`. Sesi AI berikutnya membaca pack itu, jadi tahu scene utama Anda, subsistemnya, area yang dilindungi, apa yang sudah diverifikasi, dan apa yang belum.

🇬🇧 [Read in English](README.md)

> Tidak berafiliasi dengan Unity Technologies. "Unity" adalah merek dagang pemiliknya.

**Status: v1.2.1, beta.** Tool-nya sudah punya self-test, tetapi generator ini belum divalidasi pada banyak proyek nyata. Laporan dari run sungguhan adalah kontribusi paling berguna (lihat template issue *Run report*).

## Kenapa dipakai

- **Berdasar proyek, bukan generik.** Setiap klaim penting punya label bukti (`source_verified`, `serialized_verified`, `execution_verified`, `inferred`, `proposed`, `unknown`) dan path ke kode atau asetnya.
- **Jujur soal verifikasi.** "Bisa compile", "scene sudah terpasang", dan "sudah dimainkan dan jalan" adalah klaim yang berbeda dan tidak pernah dicampur.
- **Aman secara default.** Proses generate hanya menulis dokumentasi. Tidak mengubah gameplay, upgrade package, atau menyentuh save.
- **Tetap segar.** Mode Refresh menghitung klaim mana yang basi setelah kode berubah, tanpa menulis ulang semuanya.
- **Dicek skrip.** Validator menangkap ID rusak, path palsu, bukti yang hilang, dan status yang bertentangan.

## Hasilnya

```
AGENTS.md                      <- ditambah satu section pendek (di antara marker)
docs/ai-workflow/
  agent.md                     peran + operating loop untuk sesi AI berikutnya
  project-context.md           fakta: stack, entry path, subsistem, temuan, area terlindungi
  development-workflow.md      route tugas + increment berikutnya
  validation-matrix.md         daftar check dan statusnya (satu-satunya tempat status)
  session-handoff.md           kondisi terkini
  index.json                   indeks navigasi
  README.md                    cara pakai pack
  tools/                       validate_pack.py, suspects.py, packlib.py
```

Proyek kecil mendapat profil **Compact** (file lebih sedikit). AI memilih profil terkecil yang cukup.

## Mulai cepat (sekitar 5 menit)

**Yang dibutuhkan:** AI yang bisa membaca folder proyek Unity Anda (tool coding agentic atau asisten IDE), atau kemampuan meng-upload proyek sebagai zip.

**1. Ambil kit-nya.** Pilih salah satu:

- Termudah: unduh **bundle** terbaru dari [Releases](../../releases), atau buka [`dist/Unity_Workflow_Agent_Generator_bundle.md`](dist/Unity_Workflow_Agent_Generator_bundle.md) lalu klik *Copy raw file*. Isinya satu file yang memuat semuanya.
- Atau unduh ZIP repositori (*Code → Download ZIP*) dan ekstrak **di samping** proyek Anda, bukan di dalam `Assets/` (Unity akan meng-import-nya).

**2. Beri AI akses ke proyek.**

- Tool agentic di folder proyek: buka foldernya, lalu pastikan kit bisa dibaca (letakkan di luar `Assets/`, misalnya `../unity-workflow-agent-generator`, atau di root proyek dengan nama `_ai-generator/`).
- AI berbasis chat: zip proyek **tanpa** `Library/`, `Temp/`, `Obj/`, `Logs/`, `UserSettings/`, dan `Builds/`, lalu upload zip dan file bundle.

**3. Tempel prompt ini** (boleh Anda tulis dalam bahasa apa pun, isi kit tetap Inggris):

```text
Read ENTRYPOINT.md in the generator kit and every module it references. Use Generate mode.
Inspect this Unity project, create the project-specific workflow pack, run the validator,
and report what you verified, what you could not verify, and the next executable increment.
```

(Mode bundle: lampirkan atau tempel file bundle, lalu tulis "The generator is the attached bundle" sebagai ganti menyebut `ENTRYPOINT.md`.)

**4. Tinjau hasilnya.** Periksa diff, terutama section yang ditambahkan ke `AGENTS.md`, lalu commit `docs/ai-workflow/`.

## Tambahan prompt (opsional)

Tambahkan baris berikut ke prompt di atas sesuai kebutuhan.

```text
Focus: finish the playable demo. Development scene: Assets/Scenes/Dev.unity.
```
```text
Target: Android mid-range, 60 FPS, 2 GB memory budget.
```
```text
architecture_policy = toward: Clean Architecture with VContainer, no singletons, asmdef layers Domain/Application/Infrastructure/Presentation.
```

Tanpa `architecture_policy`, pack akan **mengikuti** konvensi yang sudah ada di proyek dan tidak mengusulkan rewrite.

## Memakai pack sehari-hari

Awali setiap tugas dengan:

```text
Read AGENTS.md and docs/ai-workflow/agent.md. Then implement: <tugas Anda>.
Follow the operating loop. At the end, list checks run vs not run.
```

Agent menelusuri jalur kode yang ada dulu, membuat perubahan lengkap terkecil, mengintegrasikannya di scene sungguhan, memverifikasi sesuai risiko, dan melapor jujur. Ia tidak akan menandai check `passed` tanpa bukti.

## Menjaga pack tetap segar

Setelah perubahan besar:

```text
Read ENTRYPOINT.md and use Refresh mode. Use docs/ai-workflow/tools/suspects.py against the
revision recorded in the pack, revalidate only suspect claims plus the handoff target,
and update the pack without rewriting unaffected sections.
```

Alatnya juga bisa dijalankan sendiri (Python 3.9+, tanpa dependensi):

```bash
python docs/ai-workflow/tools/validate_pack.py . docs/ai-workflow
python docs/ai-workflow/tools/suspects.py . --pack docs/ai-workflow --since HEAD~5
```

## FAQ

**Apakah mengubah game saya?** Tidak. Secara default hanya menulis dokumentasi dan menyalin tiga tool kecil ke `docs/ai-workflow/tools/`. Implementasi adalah permintaan terpisah yang eksplisit.

**Cocok dengan AI apa?** Netral terhadap tool: AI apa pun yang bisa membaca file proyek. Belum di-benchmark lintas tool, jadi silakan [buka issue](../../issues) dengan hasil Anda.

**Apakah pack dijamin benar?** Tidak. Validator memeriksa mekanik (ID, format, apakah path dan simbol yang dikutip benar-benar ada). Ia tidak bisa membuktikan interpretasinya benar. Yang belum terverifikasi diberi label `unknown`, bukan ditebak.

**Proyek besar?** AI membatasi kedalaman (default 6 subsistem, 10 temuan, 8 route, 5 increment) dan mencatat sisanya sebagai *not inspected*. Tambahkan `Focus:` untuk mengarahkan.

**Tool editor, package, atau proyek non-game?** Bisa. Profil Compact dan kontrak editor-tooling mencakupnya.

**Bahasa?** Kit dan pack berbahasa Inggris karena validator bergantung pada nama field berbahasa Inggris. Anda tetap bisa berbicara ke AI dalam bahasa apa pun.

Detail lebih lanjut: [docs/USAGE.md](docs/USAGE.md) (Inggris).

## Struktur repositori

| Path | Fungsi |
|---|---|
| `ENTRYPOINT.md`, `core/` | Aturan generator (otoritatif) |
| `templates/` | Kontrak output dan contoh index |
| `hosts/` | Catatan lokasi instruksi tiap tool AI (verifikasi dulu) |
| `tools/` | `validate_pack.py`, `suspects.py`, `packlib.py`, `bundle.py` |
| `dist/` | Bundle satu file untuk paste atau upload |
| `tests/` | Self-test dan fixture fiktif (tidak pernah dibaca saat generate) |
| `docs/` | Dokumentasi untuk manusia |

## Pengembangan

```bash
python tests/run_tests.py     # jalankan self-test
python tools/bundle.py        # bangun ulang dist/ setelah mengubah ENTRYPOINT, core/, templates/, hosts/, atau tools/
```

Lihat [CONTRIBUTING.md](CONTRIBUTING.md). Perubahan pada `core/` sebaiknya disertai fixture atau test case.

## Lisensi

[MIT](LICENSE)
