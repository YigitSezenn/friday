# FRIDAY 4.8 QA — test case’leri ve sonuçlar

Tarih: 18 Kasım 2026, 09:36 Europe/Istanbul  
Dal: `cursor/friday-48-hud-5c95` @ `1dc8e6a` (`feat/hud-48`)  
Ortam: Windows ajan (GUI tıklama yok); unittest + MCI smoke + kod incelemesi.

Özet: **P0 KALDI yok.** Birkaç P0/P1 etkileşimli case **ENGELLİ** (oturum/GUI). Bilinen ortam: vision unittest fail (`api key not valid`).

---

## QA-01 Açılış sesi
| Alan | Değer |
| --- | --- |
| Öncelik | P0 |
| Ön koşul | `assets/sounds/startup.wav` var; `effects` açık |
| Adımlar | `sounds.play('startup')`; effects kapalı yolu unit test |
| Beklenen | WAV çalar; effects kapalıysa çalmaz |
| Gerçekleşen | MCI `play_startup=True`; `test_music_off_by_default_and_effects_on` OK; bridge `play_startup_sfx` effects/`_smoke` guard |
| Durum | **GEÇTİ** (MCI+unittest+kod). Tam HUD açılış tıklaması: ENGELLİ |
| Kanıt | unittest `tests/test_sounds.py`; shell MCI smoke 09:36 |

## QA-02 X / tepsi Çıkış
| Alan | Değer |
| --- | --- |
| Öncelik | P0 |
| Adımlar | `_on_closing` → `begin_farewell` → `dataset.shutdown` + `play_close_sfx(wait)` → `close` |
| Beklenen | Ses/animasyon bitene dek açık; sonra süreç biter |
| Gerçekleşen | Kod yolu doğrulandı (`_farewell` tek sefer); süreç sonu GUI’siz ölçülemadi |
| Durum | **ENGELLİ** (etkileşim). Kod yolu uyumlu |
| Kanıt | `ui/bridge.py` 587–622, 712+ |

## QA-03 Çift X
| Alan | Değer |
| --- | --- |
| Öncelik | P0 |
| Beklenen | İkinci çağrı no-op |
| Gerçekleşen | `if self._quitting or self._farewell: return` |
| Durum | **GEÇTİ** (kod) |
| Kanıt | `ui/bridge.py:589-591` |

## QA-04 Installer sırasında kapanış
| Alan | Değer |
| --- | --- |
| Öncelik | P0 |
| Beklenen | `installer_is_running()` iken `_on_closing` True → farewell yok |
| Gerçekleşen | Guard mevcut |
| Durum | **GEÇTİ** (kod) |
| Kanıt | `ui/bridge.py:616-619`; `jarvis/taskbar.py` |

## QA-05 Ses dosyası yok → Beep
| Alan | Değer |
| --- | --- |
| Öncelik | P0 |
| Beklenen | `play` False → Beep; çökme yok |
| Gerçekleşen | `play('nope_missing')=False`; bridge Beep fallback |
| Durum | **GEÇTİ** |
| Kanıt | MCI smoke; `play_startup_sfx` / `play_close_sfx` |

## QA-06 3D durum animasyonu
| Öncelik | P1 | Durum | **ENGELLİ** (GUI) |
| Kanıt | `ui/hud/core3d.js` var; durum API’si kodda |

## QA-07 FPS/CPU 1 dk
| Öncelik | P1 | Durum | **ENGELLİ** |
| Not | Ajan oturumunda ölçülemedi |

## QA-08 Boyut/DPI
| Öncelik | P1 | Durum | **ENGELLİ** |

## QA-09 Uyut/uyandır
| Öncelik | P1 | Durum | **ENGELLİ** |

## QA-10 Palet ≤1 sn
| Öncelik | P1 | Durum | **ENGELLİ** (GUI). Varsayılan teal config’te |

## QA-11 Müzik anahtarı
| Öncelik | P1 |
| Gerçekleşen | Config `music: False` default; unit test OK; HUD `#set-music` aria-checked false |
| Durum | **GEÇTİ** (default+kod). UI toggle kalıcılığı: ENGELLİ |
| Kanıt | `jarvis/config.py:38`; `test_sounds`; `ui/hud/index.html:180` |

## QA-12 Müzik + konuşma yankı
| Öncelik | P1 | Durum | **ENGELLİ** |
| Not | Ambient volume=260 (düşük); canlı deneme yok |

## QA-13 MCI setaudio volume
| Öncelik | P1 |
| Gerçekleşen | `sounds.py` `setaudio … volume to …`; `play(..., volume=100)` True |
| Durum | **GEÇTİ** |
| Kanıt | `jarvis/sounds.py:45`; MCI smoke |

## QA-14 Effects off → sessiz
| Öncelik | P1 |
| Gerçekleşen | Unit test + bridge early return |
| Durum | **GEÇTİ** |

## QA-15 Regresyon akışları
| Öncelik | P0 |
| Gerçekleşen | Unittest 110 ran, 1 fail (vision API key — bilinen ortam). GUI onboard/Spotify: ENGELLİ |
| Durum | **GEÇTİ*** (otomatik, bilinen 1 ortam fail). Etkileşimli: ENGELLİ |

## QA-16 teal + 3.8-live, eski 2.5 UI metni yok
| Öncelik | P0 |
| Gerçekleşen | `ui_color=teal`; HUD/model `gemini-3.8-live`; 2.5 yalnız `RETIRED_LIVE_MODELS` migrasyon map |
| Durum | **GEÇTİ** |
| Kanıt | `config.py`, `ui/hud/index.html`, `hud.js` |

## QA-17 Güncelleyici 4.7→4.8
| Öncelik | P0 | Durum | **ENGELLİ** (yayın sonrası manuel) — release betiği surum-son sırasını kullanacak |

## QA-18 Paket assets/sounds
| Öncelik | P0 |
| Gerçekleşen | Kaynak WAV’ler var; `friday.spec` datas’ta sounds. Dist doğrulaması release sonrası |
| Durum | **GEÇTİ** (kaynak+spec). Dist: release adımında |

## QA-19 prefers-reduced-motion
| Öncelik | P2 |
| Gerçekleşen | CSS `@media (prefers-reduced-motion:reduce)` boot animasyonunu keser |
| Durum | **GEÇTİ** (kod) |
| Kanıt | `ui/hud/hud.css:267` |

## QA-20 Uyku sonrası
| Öncelik | P2 | Durum | **ENGELLİ** |

---

## Unittest özeti
- `tests.test_sounds`: 3/3 OK  
- Full discover: **110** ran, **1** fail (`test_screen_analysis_describes_the_window` — vision API key), 0 error  

## Karar
P0 **KALDI** yok → S-016 `release.ps1 -Version 4.8 -Deploy` serbest (ENGELLİ GUI notlarıyla).
