# Struktura repozytorium NEXUS AI

Ten dokument opisuje docelowy podział odpowiedzialności w repozytorium oraz sposób przejścia od obecnego skryptu demonstracyjnego do utrzymywalnego projektu.

## Układ katalogów

| Ścieżka | Odpowiedzialność |
| --- | --- |
| `src/nexus/data/` | Schemat zdarzeń, walidacja, import i przygotowanie danych. |
| `src/nexus/detection/` | Wykrywanie podobieństwa profili i podejrzanych kont; oddzielenie heurystyki od przyszłego klasyfikatora. |
| `src/nexus/simulation/` | Budowa grafu oraz symulowanie przepływu informacji. |
| `src/nexus/prediction/` | Przyszły model predykcyjny, trening, zapis modelu i inferencja. Nie powinien zawierać nieudokumentowanych wag ani automatycznie utożsamiać predykcji z faktem. |
| `src/nexus/evaluation/` | Baseline'y, metryki, podział danych, kalibracja i analiza niepewności. |
| `src/nexus/visualization/` | Wykresy statyczne, animacje i eksport wyników. |
| `tests/` | Testy jednostkowe i integracyjne; przykłady testowanych wejść mogą być syntetyczne. |
| `data/` | Dokumentacja danych i opcjonalne próbki demonstracyjne. Surowe dane nie trafiają do repozytorium bez zgody i przeglądu prywatności/licencji. |
| `outputs/` | Wyniki uruchomień, wykresy i animacje; domyślnie ignorowane przez Git. |
| `assets/` | Materiały statyczne używane w README i prezentacji. |
| `docs/` | Architektura, źródła, ograniczenia, zasady pracy z danymi i plan rozwoju. |

## Proponowana migracja obecnego skryptu

Obecny `symulacja_na_heurze.py` łączy dane przykładowe, budowę grafu, heurystykę podobieństwa, dyfuzję i rysowanie. Podczas refaktoryzacji funkcje powinny zostać rozdzielone według odpowiedzialności, np.:

```text
symulacja_na_heurze.py
  ├── dane/profile i wiadomości       -> src/nexus/data/synthetic.py
  ├── make_person / budowa grafu      -> src/nexus/simulation/graph.py
  ├── impersonation_scan              -> src/nexus/detection/heuristics.py
  ├── adoption_probability / cascade  -> src/nexus/simulation/diffusion.py
  ├── draw_graph                      -> src/nexus/visualization/graph.py
  ├── create_case_study_gif           -> src/nexus/visualization/animation.py
  └── main                            -> src/nexus/cli.py
```

Najpierw warto zachować identyczny wynik demonstracji i dodać testy kontraktowe dla funkcji, a dopiero potem zmieniać założenia symulacji. Dzięki temu refaktoryzacja nie będzie mylona z poprawą modelu.

## Minimalny kontrakt zdarzenia

Przyszły moduł danych powinien rozróżniać relację między kontami od ekspozycji i reakcji na konkretną treść. Przykładowy rekord zdarzenia:

```json
{
  "event_id": "evt_001",
  "message_id": "msg_001",
  "sender_id": "account_12",
  "recipient_id": "account_34",
  "event_type": "share",
  "timestamp": "2026-10-04T09:00:00Z",
  "exposure_observed": null,
  "source": "synthetic"
}
```

`exposure_observed: null` oznacza, że informacja o wyświetleniu jest nieznana. Nie należy interpretować braku udostępnienia jako świadomego odrzucenia treści.

## Pliki konfiguracyjne

- `pyproject.toml` — metadane projektu, instalacja, formatowanie, lint i konfiguracja testów.
- `requirements.txt` — zależności instalowane w aktualnym prostym przepływie pracy. Po ustabilizowaniu pakietu można uznać `pyproject.toml` za główne źródło zależności.
- `.gitignore` — środowiska wirtualne, cache, dane prywatne, artefakty modeli i wyniki lokalne.
- `docs/references.md` — źródła kodu, bibliotek, danych, modeli, API i materiałów graficznych.

## Przykładowy `.gitignore`

```gitignore
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
data/raw/**
data/processed/**
!data/raw/.gitkeep
!data/processed/.gitkeep
models/*.pkl
models/*.joblib
outputs/**
!outputs/.gitkeep
```

W repozytorium należy przechowywać małe, nieszkodliwe przykłady demonstracyjne i dokumentację schematu. Duże dane, modele lub materiały licencjonowane powinny być wersjonowane w odpowiednim, kontrolowanym miejscu i opisane w dokumentacji.
