# fx-07 — klasifikasi `recent_events` dan cognitive gate

Membuktikan bahwa klasifikasi event (B2.4.3) dan gerbang wake (B2.4.4) bersifat
aturan mekanis, bukan selera: 12 baris event mentah diklasifikasikan ke kelas yang
tepat (INFO/NOTICE/WARNING/CRITICAL/STRATEGIC), `wake` hanya true pada kelas
CRITICAL/STRATEGIC, dan setelah cognitive gate dengan budget 4 wake/hari dan jeda
90 menit, hanya 4 dari 5 yang membangunkan lane — 1 masuk `deferred` dan tetap
muncul di BRIEFING.md bagian 2.
