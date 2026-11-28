/* PROJECT A.L.F.R.E.D. – Quellenkatalog Country Intelligence / Camera Wall.
   Von Hand gepflegt. Einträge nur nach Freigabe durch den Eigentümer (siehe PROJECT_ALFRED.md),
   jeder Eintrag mit "freigegeben": true und allen Pflichtfeldern. Keine automatische Suche, kein Scraping.
   Freigegebener Entwurf (28.11.2026): catalog/kamera_katalog_2026-11-28.json – Übernahme in "items" erfolgt in Phase 4. */
window.CAMS = {
  "stand": null,
  "hinweis": "Einträge folgen mit Phase 4 (Katalog freigegeben am 28.11.2026).",
  // Konfliktgebiete: nur Nachrichten-Streams und zeitversetzte Satellitenbilder. Zusätzlich gilt jeder WarMap-Hotspot ab Stufe 3.
  "konfliktzonen": ["UKR", "RUS", "ISR", "PSE", "LBN", "SYR", "YEM", "SDN", "IRN", "SAU", "ARE"],
  "items": []
};
